import os
from pathlib import Path
from xml.etree import ElementTree

from protocol_code_generator.generate.code_block import CodeBlock
from protocol_code_generator.generate.object_code_generator import ObjectCodeGenerator
from protocol_code_generator.generate.python_file import PythonFile
from protocol_code_generator.type.enum_type import EnumType
from protocol_code_generator.type.struct_type import StructType
from protocol_code_generator.type.type_factory import TypeFactory
from protocol_code_generator.util.docstring_utils import generate_docstring
from protocol_code_generator.util.name_utils import pascal_case_to_snake_case
from protocol_code_generator.util.xml_utils import (
    get_comment,
    get_instructions,
    get_required_string_attribute,
)


class ProtocolFile:
    def __init__(self, path, protocol):
        self.path = path
        self.protocol = protocol


class ProtocolCodeGenerator:
    def __init__(self, input_root):
        self._input_root = input_root.as_posix()
        self._output_root = None
        self._protocol_files = []
        self._exports = []
        self._packet_paths = {}
        self._type_factory = TypeFactory()

    def generate(self, output_root):
        self._output_root = output_root.as_posix()
        try:
            self._index_protocol_files()
            self._generate_source_files()
        finally:
            self._protocol_files.clear()
            self._exports.clear()
            self._packet_paths.clear()
            self._type_factory.clear()

    def _index_protocol_files(self):
        for root, _, files in os.walk(self._input_root):
            if "protocol.xml" in files:
                protocol_file = Path(os.path.join(root, "protocol.xml")).as_posix()
                self._index_protocol_file(protocol_file)

    def _index_protocol_file(self, path):
        try:
            tree = ElementTree.parse(path)
            protocol = tree.getroot()

            if protocol.tag != 'protocol':
                raise RuntimeError("Expected a root <protocol> element.")

            self._protocol_files.append(ProtocolFile(path, protocol))

            enum_elements = protocol.findall("enum")
            struct_elements = protocol.findall("struct")
            packet_elements = protocol.findall("packet")

            source_path = os.path.dirname(os.path.relpath(path, self._input_root))
            source_path = Path(source_path).as_posix()

            for protocol_enum in enum_elements:
                if not self._type_factory.define_custom_type(protocol_enum, source_path):
                    raise RuntimeError(
                        get_required_string_attribute(protocol_enum, 'name')
                        + " type cannot be redefined."
                    )

            for protocol_struct in struct_elements:
                if not self._type_factory.define_custom_type(protocol_struct, source_path):
                    raise RuntimeError(
                        get_required_string_attribute(protocol_struct, 'name')
                        + " type cannot be redefined."
                    )

            declared_packets = set()
            for protocol_packet in packet_elements:
                packet_identifier = (
                    get_required_string_attribute(protocol_packet, 'family')
                    + '_'
                    + get_required_string_attribute(protocol_packet, 'action')
                )
                if packet_identifier in declared_packets:
                    raise RuntimeError(
                        f"{packet_identifier} packet cannot be redefined in the same file."
                    )
                declared_packets.add(packet_identifier)
                self._packet_paths[protocol_packet] = source_path

        except Exception as e:
            print(f"Failed to read {path}: {e}")
            raise e

    def _generate_source_files(self):
        for protocol_file in self._protocol_files:
            self._generate_source_file(protocol_file)

    def _generate_source_file(self, protocol_file):
        protocol = protocol_file.protocol
        python_files = [
            *map(self._generate_enum, protocol.findall("enum")),
            *map(self._generate_struct, protocol.findall("struct")),
            *map(self._generate_packet, protocol.findall("packet")),
        ]

        generated_init = CodeBlock()

        for python_file in python_files:
            python_file.write(self._output_root)

            absolute_package_path = Path(python_file.relative_path).with_suffix('')
            absolute_package_path = os.path.join("eolib/protocol/_generated", absolute_package_path)
            absolute_package_path = '.'.join(Path(absolute_package_path).parts)

            generated_init.add_import("*", absolute_package_path)

        relative_path = Path(os.path.relpath(protocol_file.path, self._input_root)).as_posix()
        path = os.path.join(os.path.dirname(relative_path), "__init__.py")
        path = Path(path).as_posix()

        eo_protocol_url = "https://github.com/cirras/eo-protocol/tree/master/xml/" + relative_path

        public_package = os.path.join("eolib/protocol", relative_path)
        public_package = os.path.dirname(public_package)
        public_package = '.'.join(Path(public_package).parts)

        docstring = (
            CodeBlock()
            .add_line('"""')
            .add_line(
                'Data structures generated from the '
                + f'`eo-protocol <{eo_protocol_url}>`_ XML specification.'
            )
            .add_line()
            .add_line('.. warning::')
            .add_line()
            .add_line('   This subpackage should not be directly imported.')
            .add_line(
                f'   Instead, import :mod:`{public_package}` (or the top-level :mod:`eolib`).'
            )
            .add_line('"""')
        )

        generated_init_file = PythonFile(path, generated_init, module_docstring=docstring)
        generated_init_file.write(self._output_root)

    def _generate_enum(self, protocol_enum):
        type_name = get_required_string_attribute(protocol_enum, "name")
        type_ = self._type_factory.get_type(type_name)
        if not isinstance(type_, EnumType):
            raise RuntimeError(f"{type_name} is not a valid EnumType.")

        print(f"Generating enum: {type_.name}")

        code_block = CodeBlock()
        code_block.add_line(f"class {type_name}(IntEnum, metaclass=ProtocolEnumMeta):")
        code_block.indent()
        code_block.add_code_block(generate_docstring(get_comment(protocol_enum)))

        for protocol_value in protocol_enum.findall("value"):
            value_name = get_required_string_attribute(protocol_value, "name")
            value = type_.get_enum_value_by_name(value_name)
            code_block.add_line(f"{value.python_name} = {value.ordinal_value}")
            code_block.add_code_block(generate_docstring(get_comment(protocol_value)))

        code_block.unindent()
        code_block.add_import("IntEnum", "enum")
        code_block.add_import("ProtocolEnumMeta", "eolib.protocol.protocol_enum_meta")

        relative_path = os.path.join(type_.source_path, pascal_case_to_snake_case(type_name))
        self._exports.append(relative_path)

        return PythonFile(relative_path + ".py", code_block)

    def _generate_struct(self, protocol_struct):
        type_name = get_required_string_attribute(protocol_struct, "name")
        type_ = self._type_factory.get_type(type_name)
        if not isinstance(type_, StructType):
            raise RuntimeError(f"{type_name} is not a valid StructType.")

        print(f"Generating struct: {type_.name}")

        object_code_generator = ObjectCodeGenerator(type_.name, self._type_factory)
        for instruction in get_instructions(protocol_struct):
            object_code_generator.generate_instruction(instruction)

        relative_path = os.path.join(type_.source_path, pascal_case_to_snake_case(type_name))
        self._exports.append(relative_path)

        object_code_generator.data.docstring.add_code_block(
            generate_docstring(get_comment(protocol_struct))
        )

        code_block = object_code_generator.code

        return PythonFile(relative_path + ".py", code_block)

    def _generate_packet(self, protocol_packet):
        source_path = self._packet_paths.get(protocol_packet)
        packet_suffix = self._make_packet_suffix(source_path)
        family_attribute = get_required_string_attribute(protocol_packet, "family")
        action_attribute = get_required_string_attribute(protocol_packet, "action")
        packet_type_name = family_attribute + action_attribute + packet_suffix

        print(f"Generating packet: {packet_type_name}")

        family_type = self._type_factory.get_type("PacketFamily")
        if not isinstance(family_type, EnumType):
            raise RuntimeError("PacketFamily enum is missing.")

        action_type = self._type_factory.get_type("PacketAction")
        if not isinstance(action_type, EnumType):
            raise RuntimeError("PacketAction enum is missing.")

        family_enum_value = family_type.get_enum_value_by_name(family_attribute)
        if not family_enum_value:
            raise RuntimeError(f'Unknown packet family "{family_attribute}"')

        action_enum_value = action_type.get_enum_value_by_name(action_attribute)
        if not action_enum_value:
            raise RuntimeError(f'Unknown packet action "{action_attribute}"')

        object_code_generator = ObjectCodeGenerator(packet_type_name, self._type_factory)
        for instruction in get_instructions(protocol_packet):
            object_code_generator.generate_instruction(instruction)

        data = object_code_generator.data
        data.super_interfaces.append("Packet")

        data.add_method(
            CodeBlock()
            .add_line("@staticmethod")
            .add_line("def family() -> PacketFamily:")
            .indent()
            .add_line('"""')
            .add_line("Returns the packet family associated with this packet.")
            .add_line()
            .add_line("Returns:")
            .add_line("    The packet family associated with this packet.")
            .add_line('"""')
            .add_line(f"return PacketFamily.{family_enum_value.python_name}")
            .unindent()
        )

        data.add_method(
            CodeBlock()
            .add_line("@staticmethod")
            .add_line("def action() -> PacketAction:")
            .indent()
            .add_line('"""')
            .add_line("Returns the packet action associated with this packet.")
            .add_line()
            .add_line("Returns:")
            .add_line("    The packet action associated with this packet.")
            .add_line('"""')
            .add_line(f"return PacketAction.{action_enum_value.python_name}")
            .unindent()
        )

        data.add_method(
            CodeBlock()
            .add_line("def write(self, writer):")
            .indent()
            .add_line('"""')
            .add_line("Serializes and writes this packet to the provided EoWriter.")
            .add_line()
            .add_line("Args:")
            .add_line("    writer (EoWriter): the writer that this packet will be written to.")
            .add_line('"""')
            .add_line(f"{packet_type_name}.serialize(writer, self)")
            .unindent()
        )

        object_code_generator.data.docstring.add_code_block(
            generate_docstring(get_comment(protocol_packet))
        )

        code_block = object_code_generator.code
        code_block.add_import("Packet", "eolib.protocol.net.packet")
        code_block.add_import("PacketFamily", "eolib.protocol._generated.net.packet_family")
        code_block.add_import("PacketAction", "eolib.protocol._generated.net.packet_action")

        relative_path = os.path.join(source_path, pascal_case_to_snake_case(packet_type_name))
        self._exports.append(relative_path)

        return PythonFile(relative_path + ".py", code_block)

    @staticmethod
    def _make_packet_suffix(path):
        if path == "net/client":
            return "ClientPacket"
        elif path == "net/server":
            return "ServerPacket"
        else:
            raise ValueError(f"Cannot create packet name suffix for path {path}")
