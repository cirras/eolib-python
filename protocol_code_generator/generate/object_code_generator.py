import xml.etree.ElementTree as ET
from protocol_code_generator.generate.code_block import CodeBlock
from protocol_code_generator.generate.switch_code_generator import SwitchCodeGenerator

from protocol_code_generator.util.xml_utils import (
    get_boolean_attribute,
    get_comment,
    get_int_attribute,
    get_required_string_attribute,
    get_string_attribute,
    get_text,
)


class FieldData:
    def __init__(self, name, type, offset, array):
        self.name = name
        self.type_ = type
        self.offset = offset
        self.array = array


class ObjectGenerationContext:
    def __init__(self):
        self.chunked_reading_enabled = False
        self.reached_optional_field = False
        self.reached_dummy = False
        self.needs_old_writer_length_variable = False
        self.accessible_fields = {}
        self.length_field_is_referenced_map = {}


class ObjectGenerationData:
    def __init__(self, class_name):
        self.class_name = class_name
        self.super_interfaces = []
        self.fields = CodeBlock()
        self.methods = CodeBlock()
        self.init_params = []
        self.init_docstring_params = []
        self.init_body = CodeBlock()
        self.serialize = CodeBlock()
        self.deserialize = CodeBlock()
        self.deserialize_init_arguments = []
        self.auxiliary_types = CodeBlock()
        self.docstring = CodeBlock()
        self.repr_fields = ["byte_size"]

    def add_method(self, method):
        if self.methods:
            self.methods.add_line()
        self.methods.add_code_block(method)

    def add_auxiliary_type(self, type):
        if self.auxiliary_types:
            self.auxiliary_types.add_line()
        self.auxiliary_types.add_code_block(type)


class ObjectCodeGenerator:
    def __init__(self, class_name, type_factory, context=None):
        self._class_name = class_name
        self._type_factory = type_factory
        self._context = ObjectGenerationContext() if context is None else context
        self._data = ObjectGenerationData(class_name)

    def generate_instruction(self, instruction):
        if self._context.reached_dummy:
            raise RuntimeError("<dummy> elements must not be followed by any other elements.")

        instruction_name = instruction.tag

        if instruction_name == "field":
            self._generate_field(instruction)
        elif instruction_name == "array":
            self._generate_array(instruction)
        elif instruction_name == "length":
            self._generate_length(instruction)
        elif instruction_name == "dummy":
            self._generate_dummy(instruction)
        elif instruction_name == "switch":
            self._generate_switch(instruction)
        elif instruction_name == "chunked":
            self._generate_chunked(instruction)
        elif instruction_name == "break":
            self._generate_break()

    @property
    def data(self):
        return self._data

    @property
    def code(self):
        simple_name = self._class_name
        if '.' in simple_name:
            simple_name = simple_name.rsplit('.', 1)[1]

        super_interfaces = (
            f"({', '.join(self._data.super_interfaces)})" if self._data.super_interfaces else ""
        )

        result = (
            CodeBlock()
            .add_line(f"class {simple_name}{super_interfaces}:")
            .indent()
            .add_code_block(self._data.docstring)
            .add_line("_byte_size: int = 0")
            .add_code_block(self._data.fields)
            .add_line()
            .add_code_block(self._generate_init_method())
            .add_line()
            .add_code_block(self._generate_get_byte_size())
            .add_line()
            .add_code_block(self._data.methods)
            .add_line()
            .add_code_block(self._generate_serialize_method())
            .add_line()
            .add_code_block(self._generate_deserialize_method())
            .add_line()
            .add_code_block(self._generate_repr_method())
        )

        if self._data.auxiliary_types:
            result.add_line()
            result.add_code_block(self._data.auxiliary_types)

        result.unindent()

        return result

    def _generate_init_method(self):
        result = CodeBlock().add(f'def __init__(self')
        if self._data.init_params:
            result.add(', *')
        for param in self._data.init_params:
            result.add(', ')
            result.add_code_block(param)
        result.add_line('):')

        result.indent()
        result.add_line('"""')
        result.add_line(f'Create a new instance of {self._class_name}.')
        if self._data.init_docstring_params:
            result.add_line()
            result.add_line('Args:')
            for docstring_param in self._data.init_docstring_params:
                result.add('    ')
                result.add_code_block(docstring_param)
                result.add_line()
        result.add_line('"""')

        result.add_code_block(self._data.init_body)

        return result

    def _generate_get_byte_size(self):
        return (
            CodeBlock()
            .add_line('@property')
            .add_line('def byte_size(self) -> int:')
            .indent()
            .add_line('"""')
            .add_line('Returns the size of the data that this was deserialized from.')
            .add_line()
            .add_line('Returns:')
            .add_line('    int: The size of the data that this was deserialized from.')
            .add_line('"""')
            .add_line('return self._byte_size')
            .unindent()
        )

    def _generate_serialize_method(self):
        result = (
            CodeBlock()
            .add_line("@staticmethod")
            .add_line(f'def serialize(writer: EoWriter, data: "{self._class_name}") -> None:')
            .indent()
            .add_line('"""')
            .add_line(f'Serializes an instance of `{self._class_name}` to the provided `EoWriter`.')
            .add_line()
            .add_line('Args:')
            .add_line('    writer (EoWriter): The writer that the data will be serialized to.')
            .add_line(f'    data ({self._class_name}): The data to serialize.')
            .add_line('"""')
        )

        if self._context.needs_old_writer_length_variable:
            result.add_line('old_writer_length: int = len(writer)')

        result.add_line('old_string_sanitization_mode: bool = writer.string_sanitization_mode')
        result.begin_control_flow('try')
        result.add_code_block(self._data.serialize)
        result.next_control_flow('finally')
        result.add_line('writer.string_sanitization_mode = old_string_sanitization_mode')
        result.unindent()
        result.unindent()
        result.add_import('EoWriter', 'eolib.data.eo_writer')

        return result

    def _generate_deserialize_method(self):
        constructor = CodeBlock().add(f'{self._class_name}(')
        for i, arg in enumerate(self._data.deserialize_init_arguments):
            if i > 0:
                constructor.add(', ')
            constructor.add_code_block(arg)
        constructor.add_line(')')

        return (
            CodeBlock()
            .add_line("@staticmethod")
            .add_line(f'def deserialize(reader: EoReader) -> "{self._class_name}":')
            .indent()
            .add_line('"""')
            .add_line(
                f'Deserializes an instance of `{self._class_name}` from the provided `EoReader`.'
            )
            .add_line()
            .add_line('Args:')
            .add_line('    reader (EoReader): The writer that the data will be serialized to.')
            .add_line()
            .add_line('Returns:')
            .add_line(f'    {self._class_name}: The data to serialize.')
            .add_line('"""')
            .add_line('old_chunked_reading_mode: bool = reader.chunked_reading_mode')
            .begin_control_flow('try')
            .add_line('reader_start_position: int = reader.position')
            .add_code_block(self._data.deserialize)
            .add('result = ')
            .add_code_block(constructor)
            .add_line('result._byte_size = reader.position - reader_start_position')
            .add_line('return result')
            .next_control_flow('finally')
            .add_line('reader.chunked_reading_mode = old_chunked_reading_mode')
            .unindent()
            .add_import('EoReader', 'eolib.data.eo_reader')
        )

    def _generate_repr_method(self):
        field_to_repr_str = lambda field: field + "={repr(self._" + field + ")}"
        repr_str = ', '.join(map(field_to_repr_str, self._data.repr_fields))
        return (
            CodeBlock()
            .add_line('def __repr__(self):')
            .indent()
            .add_line(f'return f"{self._class_name}({repr_str})"')
            .unindent()
        )

    def _generate_field(self, protocol_field):
        optional = protocol_field.get("optional")
        self._check_optional_field(optional)

        field_code_generator = (
            self._field_code_generator_builder()
            .name(get_string_attribute(protocol_field, "name"))
            .type(get_required_string_attribute(protocol_field, "type"))
            .length(get_string_attribute(protocol_field, "length"))
            .padded(get_boolean_attribute(protocol_field, "padded"))
            .optional(optional)
            .hardcoded_value(get_text(protocol_field))
            .comment(get_comment(protocol_field))
            .build()
        )

        field_code_generator.generate_field()
        field_code_generator.generate_serialize()
        field_code_generator.generate_deserialize()

        if optional:
            self._context.reached_optional_field = True

    def _generate_array(self, protocol_array):
        optional = protocol_array.get("optional")
        self._check_optional_field(optional)

        delimited = protocol_array.get("delimited")
        if delimited and not self._context.chunked_reading_enabled:
            raise RuntimeError(
                "Cannot generate a delimited array instruction unless chunked reading is enabled."
            )

        field_code_generator = (
            self._field_code_generator_builder()
            .name(get_required_string_attribute(protocol_array, "name"))
            .type(get_required_string_attribute(protocol_array, "type"))
            .length(get_string_attribute(protocol_array, "length"))
            .optional(optional)
            .comment(get_comment(protocol_array))
            .array_field(True)
            .delimited(delimited)
            .trailing_delimiter(get_boolean_attribute(protocol_array, "trailing-delimiter", True))
            .build()
        )

        field_code_generator.generate_field()
        field_code_generator.generate_serialize()
        field_code_generator.generate_deserialize()

        if optional:
            self._context.reached_optional_field = True

    def _generate_length(self, protocol_length):
        optional = protocol_length.get("optional")
        self._check_optional_field(optional)

        field_code_generator = (
            self._field_code_generator_builder()
            .name(get_required_string_attribute(protocol_length, "name"))
            .type(get_required_string_attribute(protocol_length, "type"))
            .offset(get_int_attribute(protocol_length, "offset"))
            .length_field(True)
            .optional(optional)
            .comment(get_comment(protocol_length))
            .build()
        )

        field_code_generator.generate_field()
        field_code_generator.generate_serialize()
        field_code_generator.generate_deserialize()

        if optional:
            self._context.reached_optional_field = True

    def _generate_dummy(self, protocol_dummy):
        field_code_generator = (
            self._field_code_generator_builder()
            .type(get_required_string_attribute(protocol_dummy, "type"))
            .hardcoded_value(get_text(protocol_dummy))
            .comment(get_comment(protocol_dummy))
            .build()
        )

        needs_if_guards = not self._data.serialize.empty or not self._data.deserialize.empty

        if needs_if_guards:
            self._data.serialize.begin_control_flow("if len(writer) == old_writer_length")
            self._data.deserialize.begin_control_flow("if reader.position == reader_start_position")

        field_code_generator.generate_serialize()
        field_code_generator.generate_deserialize()

        if needs_if_guards:
            self._data.serialize.unindent()
            self._data.deserialize.unindent()

        self._context.reached_dummy = True

        if needs_if_guards:
            self._context.needs_old_writer_length_variable = True

    def _field_code_generator_builder(self):
        from protocol_code_generator.generate.field_code_generator import FieldCodeGeneratorBuilder

        return FieldCodeGeneratorBuilder(self._type_factory, self._context, self._data)

    def _check_optional_field(self, optional):
        if self._context.reached_optional_field and not optional:
            raise RuntimeError("Optional fields may not be followed by non-optional fields.")

    def _generate_switch(self, protocol_switch):
        switch_code_generator = SwitchCodeGenerator(
            get_required_string_attribute(protocol_switch, "field"),
            self._type_factory,
            self._context,
            self._data,
        )

        protocol_cases = protocol_switch.findall("case")

        switch_code_generator.generate_case_data_interface(protocol_cases)
        switch_code_generator.generate_case_data_field()

        reached_optional_field = self._context.reached_optional_field
        reached_dummy = self._context.reached_dummy
        start = True

        for protocol_case in protocol_cases:
            case_context = switch_code_generator.generate_case(protocol_case, start)

            reached_optional_field = reached_optional_field or case_context.reached_optional_field
            reached_dummy = reached_dummy or case_context.reached_dummy
            start = False

        self._context.reached_optional_field = reached_optional_field
        self._context.reached_dummy = reached_dummy

    def _generate_chunked(self, protocol_chunked):
        was_already_enabled = self._context.chunked_reading_enabled
        if not was_already_enabled:
            self._context.chunked_reading_enabled = True
            self._data.deserialize.add_line("reader.chunked_reading_mode = True")
            self._data.serialize.add_line("writer.string_sanitization_mode = True")

        for instruction in protocol_chunked:
            self.generate_instruction(instruction)

        if not was_already_enabled:
            self._context.chunked_reading_enabled = False
            self._data.deserialize.add_line("reader.chunked_reading_mode = False")
            self._data.serialize.add_line("writer.string_sanitization_mode = False")

    def _generate_break(self):
        if not self._context.chunked_reading_enabled:
            raise RuntimeError(
                "Cannot generate a break instruction unless chunked reading is enabled."
            )

        self._context.reached_optional_field = False
        self._context.reached_dummy = False

        self._data.serialize.add_line("writer.add_byte(0xFF)")
        self._data.deserialize.add_line("reader.next_chunk()")
