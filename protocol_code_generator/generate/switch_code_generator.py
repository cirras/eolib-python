import copy

from protocol_code_generator.generate.code_block import CodeBlock
from protocol_code_generator.type.enum_type import EnumType
from protocol_code_generator.type.integer_type import IntegerType
from protocol_code_generator.util.docstring_utils import generate_docstring
from protocol_code_generator.util.name_utils import snake_case_to_pascal_case
from protocol_code_generator.util.number_utils import try_parse_int
from protocol_code_generator.util.xml_utils import (
    get_boolean_attribute,
    get_comment,
    get_instructions,
    get_required_string_attribute,
)


class SwitchCodeGenerator:
    def __init__(self, field_name, type_factory, context, data):
        self._field_name = field_name
        self._type_factory = type_factory
        self._context = context
        self._data = data

    def generate_case_data_interface(self, protocol_cases):
        union_type_names = [
            f"'{self.get_case_data_type_name(case)}'"
            for case in protocol_cases
            if len(get_instructions(case)) > 0
        ]
        union_type_names.append("None")

        union_type = f"Union[{', '.join(union_type_names)}]"
        field_name = self._field_name

        self._data.add_auxiliary_type(
            CodeBlock()
            .add_line(f"{self._interface_type_name} = {union_type}")
            .add_line('"""')
            .add_line(f'Data associated with different values of the `{field_name}` field.')
            .add_line('"""')
            .add_import("Union", "typing")
        )

    def generate_case_data_field(self):
        interface_type_name = f"{self._data.class_name}.{self._interface_type_name}"
        case_data_field_name = self._case_data_field_name
        switch_field_name = self._field_name

        self._data.fields.add_line(f"_{case_data_field_name}: '{interface_type_name}' = None")
        self._data.add_method(
            CodeBlock()
            .add_line("@property")
            .add_line(f"def {case_data_field_name}(self) -> '{interface_type_name}':")
            .indent()
            .add_line('"""')
            .add_line(
                f'{interface_type_name}: Gets or sets the data associated with the '
                + f'`{switch_field_name}` field.'
            )
            .add_line('"""')
            .add_line(f"return self._{case_data_field_name}")
            .unindent()
        )
        self._data.add_method(
            CodeBlock()
            .add_line(f"@{case_data_field_name}.setter")
            .add_line(
                f"def {case_data_field_name}("
                + f"self, {case_data_field_name}: '{interface_type_name}') -> None:"
            )
            .indent()
            .add_line(f"self._{case_data_field_name} = {case_data_field_name}")
            .unindent()
        )
        self._data.repr_fields.append(case_data_field_name)

    def generate_case(self, protocol_case, start):
        case_data_type_name = self.get_case_data_type_name(protocol_case)
        case_context = copy.deepcopy(self._context)
        case_context.accessible_fields.clear()
        case_context.length_field_is_referenced_map.clear()

        default = get_boolean_attribute(protocol_case, "default")

        if default:
            if start:
                raise RuntimeError("Standalone default case is not allowed.")
            control_flow = "else"
        else:
            keyword = 'if' if start else 'elif'
            switch_value_expression = "data._" + self._field_name
            case_value_expression = self._get_case_value_expression(protocol_case)
            control_flow = f"{keyword} {switch_value_expression} == {case_value_expression}"

        self._data.serialize.begin_control_flow(control_flow)
        self._data.deserialize.begin_control_flow(control_flow)

        field_to_string_expression = (
            f"{self._field_data.type_.name}(data._{self._field_name}).name"
            if isinstance(self._field_data.type_, EnumType)
            else f"str(data._{self._field_name})"
        )

        if get_instructions(protocol_case) == []:
            self._data.serialize.begin_control_flow(
                f"if data._{self._case_data_field_name} is not None"
            )
            self._data.serialize.add_line(
                'raise SerializationError('
                + f'"Expected {self._case_data_field_name} to be None for {self._field_name} "'
                + f' + {field_to_string_expression} + ".")'
            )
            self._data.serialize.unindent()
            self._data.serialize.add_import(
                "SerializationError", "eolib.protocol.serialization_error"
            )

            self._data.deserialize.add_line(f"data._{self._case_data_field_name} = None")

        else:
            self._data.add_auxiliary_type(
                self.generate_case_data_type(protocol_case, case_data_type_name, case_context)
            )
            self._data.serialize.begin_control_flow(
                f"if not isinstance(data._{self._case_data_field_name}, {case_data_type_name})"
            )
            self._data.serialize.add_line(
                'raise SerializationError('
                + f'"Expected {self._case_data_field_name} to be type {case_data_type_name} '
                + f'for {self._field_name} " + {field_to_string_expression} + ".")'
            )
            self._data.serialize.unindent()
            self._data.serialize.add_line(
                f'{case_data_type_name}.serialize(writer, data._{self._case_data_field_name})'
            )
            self._data.serialize.add_import(
                "SerializationError", "eolib.protocol.serialization_error"
            )

            self._data.deserialize.add_line(
                f'data._{self._case_data_field_name} = {case_data_type_name}.deserialize(reader)'
            )

        self._data.serialize.unindent()
        self._data.deserialize.unindent()

        return case_context

    def generate_case_data_type(self, protocol_case, case_data_type_name, case_context):
        from protocol_code_generator.generate.object_code_generator import ObjectCodeGenerator

        object_code_generator = ObjectCodeGenerator(
            case_data_type_name, self._type_factory, case_context
        )

        for instruction in get_instructions(protocol_case):
            object_code_generator.generate_instruction(instruction)

        default = get_boolean_attribute(protocol_case, "default")

        if default:
            comment = f'Default data associated with {self._field_name}'
        else:
            case_value_expression = self._get_case_value_expression(protocol_case)
            comment = f'Data associated with {self._field_name} value {case_value_expression}'

        protocol_comment = get_comment(protocol_case)
        if protocol_comment is not None:
            comment += '\n\n'
            comment += protocol_comment

        object_code_generator.data.docstring = generate_docstring(comment)

        return object_code_generator.code

    @property
    def _field_data(self):
        result = self._context.accessible_fields.get(self._field_name)
        if not result:
            raise RuntimeError(f"Referenced {self._field_name} is not accessible.")
        return result

    @property
    def _interface_type_name(self):
        return snake_case_to_pascal_case(self._field_name) + "Data"

    @property
    def _case_data_field_name(self):
        return self._field_name + "_data"

    def get_case_data_type_name(self, protocol_case):
        is_default = get_boolean_attribute(protocol_case, "default")
        return (
            self._data.class_name
            + '.'
            + self._interface_type_name
            + ("Default" if is_default else get_required_string_attribute(protocol_case, "value"))
        )

    def _get_case_value_expression(self, protocol_case):
        field_data = self._field_data

        if field_data.array:
            raise RuntimeError(
                f'"{self._field_name}" field referenced by switch must not be an array.'
            )

        field_type = field_data.type_
        case_value = get_required_string_attribute(protocol_case, "value")

        if isinstance(field_type, IntegerType):
            if not case_value.isdigit():
                raise RuntimeError(f'"{case_value}" is not a valid integer value.')
            return case_value

        if isinstance(field_type, EnumType):
            ordinal_value = try_parse_int(case_value)
            if ordinal_value is not None:
                enum_value = field_type.get_enum_value_by_ordinal(ordinal_value)
                if enum_value is not None:
                    raise RuntimeError(
                        f'{field_type.name} value {case_value} '
                        + f'must be referred to by name ({enum_value.name})'
                    )
                return case_value

            enum_value = field_type.get_enum_value_by_name(case_value)
            if enum_value is None:
                raise RuntimeError(
                    f'"{case_value}" is not a valid value for enum type {field_type.name}.'
                )
            return f'{field_type.name}.{enum_value.python_name}'

        raise RuntimeError(
            f'{self._field_name} field referenced by switch must be a numeric or enumeration type.'
        )
