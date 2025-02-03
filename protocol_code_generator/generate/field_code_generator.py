from html import escape
from protocol_code_generator.generate.code_block import CodeBlock
from protocol_code_generator.generate.object_code_generator import FieldData
from protocol_code_generator.type.basic_type import BasicType
from protocol_code_generator.type.blob_type import BlobType
from protocol_code_generator.type.bool_type import BoolType
from protocol_code_generator.type.custom_type import CustomType
from protocol_code_generator.type.enum_type import EnumType
from protocol_code_generator.type.has_underlying_type import HasUnderlyingType
from protocol_code_generator.type.integer_type import IntegerType
from protocol_code_generator.type.length import Length
from protocol_code_generator.type.string_type import StringType
from protocol_code_generator.type.struct_type import StructType
from protocol_code_generator.util.docstring_utils import generate_docstring
from protocol_code_generator.util.number_utils import try_parse_int


class FieldCodeGenerator:
    def __init__(
        self,
        type_factory,
        context,
        data,
        name,
        type_string,
        length_string,
        padded,
        optional,
        hardcoded_value,
        comment,
        array_field,
        delimited,
        trailing_delimiter,
        length_field,
        offset,
    ):
        self._type_factory = type_factory
        self._context = context
        self._data = data
        self._name = name
        self._type_string = type_string
        self._length_string = length_string
        self._padded = padded
        self._optional = optional
        self._hardcoded_value = hardcoded_value
        self._comment = comment
        self._array_field = array_field
        self._delimited = delimited
        self._trailing_delimiter = trailing_delimiter
        self._length_field = length_field
        self._offset = offset
        self._validate()

    def _validate(self):
        self._validate_special_fields()
        self._validate_optional_field()
        self._validate_array_field()
        self._validate_length_field()
        self._validate_unnamed_field()
        self._validate_hardcoded_value()
        self._validate_unique_name()
        self._validate_length_attribute()

    def _validate_special_fields(self):
        if self._array_field and self._length_field:
            raise RuntimeError("A field cannot be both a length field and an array field.")

    def _validate_optional_field(self):
        if not self._optional:
            return

        if self._name is None:
            raise RuntimeError("Optional fields must specify a name.")

    def _validate_array_field(self):
        if self._array_field:
            if self._name is None:
                raise RuntimeError("Array fields must specify a name.")
            if self._hardcoded_value:
                raise RuntimeError("Array fields may not specify hardcoded values.")
            if not self._delimited and not self._get_type().bounded:
                raise RuntimeError(
                    f"Unbounded element type ({self._type_string}) "
                    + "forbidden in non-delimited array."
                )
        else:
            if self._delimited:
                raise RuntimeError("Only arrays can be delimited.")

    def _validate_length_field(self):
        if self._length_field:
            if self._name is None:
                raise RuntimeError("Length fields must specify a name.")
            if self._hardcoded_value is not None:
                raise RuntimeError("Length fields may not specify hardcoded values.")
            field_type = self._get_type()
            if not isinstance(field_type, IntegerType):
                raise RuntimeError(
                    f"{field_type.name} is not a numeric type, "
                    + "so it is not allowed for a length field."
                )
        else:
            if self._offset != 0:
                raise RuntimeError("Only length fields can have an offset.")

    def _validate_unnamed_field(self):
        if self._name is not None:
            return

        if self._hardcoded_value is None:
            raise RuntimeError("Unnamed fields must specify a hardcoded field value.")

        if self._optional:
            raise RuntimeError("Unnamed fields may not be optional.")

    def _validate_hardcoded_value(self):
        if self._hardcoded_value is None:
            return

        field_type = self._get_type()

        if isinstance(field_type, StringType):
            length = try_parse_int(self._length_string)
            if length is not None and length != len(self._hardcoded_value):
                raise RuntimeError(
                    f"Expected length of {length} for hardcoded string value "
                    + f"'{self._hardcoded_value}'."
                )

        if not isinstance(field_type, BasicType):
            raise RuntimeError(
                f"Hardcoded field values are not allowed for {field_type.name} fields "
                + "(must be a basic type)."
            )

    def _validate_unique_name(self):
        if self._name is None:
            return

        if self._name in self._context.accessible_fields:
            raise RuntimeError(f"Cannot redefine {self._name} field.")

    def _validate_length_attribute(self):
        if self._length_string is None:
            return

        if (
            not self._length_string.isdigit()
            and self._length_string not in self._context.length_field_is_referenced_map
        ):
            raise RuntimeError(
                f'Length attribute "{self._length_string}" must be a numeric literal, '
                + 'or refer to a length field.'
            )

        is_already_referenced = self._context.length_field_is_referenced_map.get(
            self._length_string, False
        )

        if is_already_referenced:
            raise RuntimeError(
                f'Length field "{self._length_string}" must not be referenced by multiple fields.'
            )

    def generate_field(self):
        if self._name is None:
            return

        field_type = self._get_type()

        python_type_name = self._get_python_type_name(field_type)
        python_param_type_name = python_type_name

        if self._array_field:
            python_type_name = f"tuple[{python_type_name}, ...]"
            python_param_type_name = f"Iterable[{python_param_type_name}]"
            self._data.fields.add_import('annotations', '__future__')
            self._data.fields.add_import('Iterable', 'collections.abc')

        if self._optional:
            python_type_name = f"Optional[{python_type_name}]"
            python_param_type_name = f"Optional[{python_param_type_name}]"
            self._data.fields.add_import('Optional', 'typing')

        self._context.accessible_fields[self._name] = FieldData(
            self._name, field_type, self._offset, self._array_field
        )

        self._data.fields.add_line(f"_{self._name}: {python_type_name}")

        if isinstance(field_type, CustomType):
            self._data.fields.add_import_by_type(field_type)

        if self._length_field:
            self._context.length_field_is_referenced_map[self._name] = False
            return

        self._data.init_docstring_params.append(
            CodeBlock()
            .add(f'{self._name} ({python_param_type_name}): ')
            .add_code_block(self._generate_init_docstring())
        )

        self._data.add_method(
            CodeBlock()
            .add_line('@property')
            .add_line(f'def {self._name}(self) -> {python_type_name}:')
            .indent()
            .add_code_block(generate_docstring(self._comment))
            .add_line(f'return self._{self._name}')
            .unindent()
        )

        self._data.repr_fields.append(self._name)

        if self._hardcoded_value is None:
            expression = self._name
            if self._array_field:
                expression = f'tuple({expression})'
        elif isinstance(field_type, StringType):
            expression = f'"{self._hardcoded_value}"'
        else:
            expression = self._hardcoded_value

        init_param = CodeBlock().add(f'{self._name}: {python_param_type_name}')
        if self._optional:
            init_param.add(' = None')

        self._data.init_params.append(init_param)
        self._data.init_body.add_line(f'self._{self._name} = {expression}')

        if self._length_string in self._context.length_field_is_referenced_map:
            self._context.length_field_is_referenced_map[self._length_string] = True
            length_field_data = self._context.accessible_fields[self._length_string]
            self._data.init_body.add_line(
                f'self._{length_field_data.name} = len(self._{self._name})'
            )

    def generate_serialize(self):
        self._generate_serialize_missing_optional_guard()
        self._generate_serialize_none_not_allowed_error()
        self._generate_serialize_length_check()

        if self._array_field:
            array_size_expression = self._get_serialize_length_expression()
            if array_size_expression is None:
                array_size_expression = f"len(data._{self._name})"

            self._data.serialize.begin_control_flow(f"for i in range({array_size_expression})")

            if self._delimited and not self._trailing_delimiter:
                self._data.serialize.begin_control_flow("if i > 0")
                self._data.serialize.add_line("writer.add_byte(0xFF)")
                self._data.serialize.unindent()

        self._data.serialize.add_code_block(self._get_write_statement())

        if self._array_field:
            if self._delimited and self._trailing_delimiter:
                self._data.serialize.add_line("writer.add_byte(0xFF)")
            self._data.serialize.unindent()

        if self._optional:
            self._data.serialize.unindent()

    def generate_deserialize(self):
        if self._optional:
            python_type = f'Optional[{self._get_python_type_name(self._get_type())}]'
            self._data.deserialize.add_line(f'{self._name}: {python_type} = None')
            self._data.deserialize.begin_control_flow("if reader.remaining > 0")

        if self._array_field:
            self._generate_deserialize_array()
        else:
            self._data.deserialize.add_code_block(self._get_read_statement())

        if self._optional:
            self._data.deserialize.unindent()

        if self._name is not None and not self._length_field:
            self._data.deserialize_init_arguments.append(
                CodeBlock().add(f'{self._name}={self._name}')
            )

    def _generate_init_docstring(self):
        result = CodeBlock()

        if self._comment is not None:
            lines = map(str.strip, escape(self._comment, quote=False).split('\n'))
            for line in lines:
                if not result.empty:
                    result.add(' ')
                result.add(line)

        if self._length_string is not None:
            size_description = ""
            field_data = self._context.accessible_fields.get(self._length_string)
            if field_data:
                max_value = get_max_value_of(field_data.type_) + field_data.offset
                size_description = f"{max_value} or less"
            else:
                size_description = f'`{self._length_string}`'
                if self._padded:
                    size_description += " or less"
            if not result.empty:
                result.add(' ')
            result.add(f'(Length must be {size_description}.)')

        field_type = self._get_type()
        if isinstance(field_type, IntegerType):
            value_description = "Element value" if self._array_field else "Value"
            if not result.empty:
                result.add(' ')
            result.add(f'({value_description} range is 0-{get_max_value_of(field_type)}.)')

        return result

    def _generate_serialize_missing_optional_guard(self):
        if not self._optional:
            return

        if self._context.reached_optional_field:
            self._data.serialize.add_line(
                f"reached_missing_optional = reached_missing_optional or data._{self._name} is None"
            )
        else:
            self._data.serialize.add_line(f"reached_missing_optional = data._{self._name} is None")
        self._data.serialize.begin_control_flow("if not reached_missing_optional")

    def _generate_serialize_none_not_allowed_error(self):
        if self._optional or self._name is None or self._hardcoded_value is not None:
            return

        self._data.serialize.begin_control_flow(f"if data._{self._name} is None")
        self._data.serialize.add_line(f'raise SerializationError("{self._name} must be provided.")')
        self._data.serialize.unindent()
        self._data.serialize.add_import("SerializationError", "eolib.protocol.serialization_error")

    def _generate_serialize_length_check(self):
        if self._name is None:
            return

        length_expression = None
        field_data = self._context.accessible_fields.get(self._length_string)
        if field_data:
            length_expression = str(get_max_value_of(field_data.type_) + field_data.offset)
        else:
            length_expression = self._length_string

        if length_expression is None:
            return

        variable_size = self._padded or bool(field_data)
        length_check_operator = ">" if variable_size else "!="
        expected_length_description = (
            f"{length_expression} or less" if variable_size else f"exactly {length_expression}"
        )
        error_message = (
            "Expected length of "
            + self._name
            + " to be "
            + expected_length_description
            + (", got {len(data._" + self._name + ")}.")
        )

        self._data.serialize.begin_control_flow(
            f"if len(data._{self._name}) {length_check_operator} {length_expression}"
        )
        self._data.serialize.add_line(f'raise SerializationError(f"{error_message}")')
        self._data.serialize.unindent()
        self._data.serialize.add_import("SerializationError", "eolib.protocol.serialization_error")

    def _get_write_statement(self):
        real_type = self._get_type()
        type_ = real_type

        if isinstance(type_, HasUnderlyingType):
            type_ = type_.underlying_type

        value_expression = self._get_write_value_expression()
        if self._optional:
            value_expression = f'cast({self._get_python_type_name(real_type)}, {value_expression})'

        if isinstance(real_type, BoolType):
            value_expression = f"1 if {value_expression} else 0"

        if isinstance(real_type, EnumType):
            value_expression = f"int({value_expression})"

        offset_expression = FieldCodeGenerator._get_length_offset_expression(-self._offset)
        if offset_expression is not None:
            value_expression += offset_expression

        result = CodeBlock()

        if isinstance(type_, BasicType):
            length_expression = (
                None if self._array_field else self._get_serialize_length_expression()
            )
            write_statement = FieldCodeGenerator._get_write_statement_for_basic_type(
                type_, value_expression, length_expression, self._padded
            )
            result.add_line(write_statement)
        elif isinstance(type_, BlobType):
            result.add_line(f"writer.add_bytes({value_expression})")
        elif isinstance(type_, StructType):
            result.add_line(f"{type_.name}.serialize(writer, {value_expression})")
            result.add_import_by_type(type_)

        if not result:
            raise AssertionError("Unhandled Type")

        if self._optional:
            result.add_import("cast", "typing")

        return result

    def _get_write_value_expression(self):
        if self._name is None:
            type_ = self._get_type()
            if isinstance(type_, IntegerType):
                if self._hardcoded_value.isdigit():
                    return self._hardcoded_value
                raise RuntimeError(f'"{self._hardcoded_value}" is not a valid integer value.')
            elif isinstance(type_, BoolType):
                if self._hardcoded_value == "false":
                    return "0"
                elif self._hardcoded_value == "true":
                    return "1"
                raise RuntimeError(f'"{self._hardcoded_value}" is not a valid bool value.')
            elif isinstance(type_, StringType):
                return f'"{self._hardcoded_value}"'
            else:
                raise AssertionError("Unhandled BasicType")
        else:
            field_reference = f"data._{self._name}"
            if self._array_field:
                field_reference += "[i]"
            return field_reference

    @staticmethod
    def _get_write_statement_for_basic_type(type_, value_expression, length_expression, padded):
        if type_.name == "byte":
            return f"writer.add_byte({value_expression})"
        elif type_.name == "char":
            return f"writer.add_char({value_expression})"
        elif type_.name == "short":
            return f"writer.add_short({value_expression})"
        elif type_.name == "three":
            return f"writer.add_three({value_expression})"
        elif type_.name == "int":
            return f"writer.add_int({value_expression})"
        elif type_.name == "string":
            if length_expression is None:
                return f"writer.add_string({value_expression})"
            else:
                return f"writer.add_fixed_string({value_expression}, {length_expression}, {padded})"
        elif type_.name == "encoded_string":
            if length_expression is None:
                return f"writer.add_encoded_string({value_expression})"
            else:
                return (
                    "writer.add_fixed_encoded_string("
                    + f"{value_expression}, {length_expression}, {padded})"
                )
        else:
            raise AssertionError("Unhandled BasicType")

    def _generate_deserialize_array(self):
        array_length_expression = self._get_deserialize_length_expression()

        if array_length_expression is None and not self._delimited:
            element_size = self._get_type().fixed_size
            if element_size is not None:
                array_length_variable_name = f"{self._name}_length"
                self._data.deserialize.add_line(
                    f"{array_length_variable_name} = int(reader.remaining / {element_size})"
                )
                array_length_expression = array_length_variable_name

        self._data.deserialize.add_line(f"{self._name} = []")

        if array_length_expression is None:
            self._data.deserialize.begin_control_flow("while reader.remaining > 0")
        else:
            self._data.deserialize.begin_control_flow(f"for i in range({array_length_expression})")

        self._data.deserialize.add_code_block(self._get_read_statement())

        if self._delimited:
            needs_guard = not self._trailing_delimiter and array_length_expression is not None
            if needs_guard:
                self._data.deserialize.begin_control_flow(f"if i + 1 < {array_length_expression}")
            self._data.deserialize.add_line("reader.next_chunk()")
            if needs_guard:
                self._data.deserialize.unindent()

        self._data.deserialize.unindent()

    def _get_read_statement(self):
        real_type = self._get_type()
        type_ = real_type

        if isinstance(type_, HasUnderlyingType):
            type_ = type_.underlying_type

        statement = CodeBlock()

        if self._array_field:
            statement.add(f"{self._name}.append(")
        elif self._name is not None:
            statement.add(f"{self._name} = ")

        if isinstance(type_, BasicType):
            length_expression = (
                None if self._array_field else self._get_deserialize_length_expression()
            )
            read_basic_type = FieldCodeGenerator._get_read_statement_for_basic_type(
                type_, length_expression, self._padded
            )

            offset_expression = FieldCodeGenerator._get_length_offset_expression(self._offset)
            if offset_expression is not None:
                read_basic_type += offset_expression

            if isinstance(real_type, BoolType):
                statement.add(f"{read_basic_type} != 0")
            elif isinstance(real_type, EnumType):
                statement.add(f"{real_type.name}({read_basic_type})")
            else:
                statement.add(read_basic_type)
        elif isinstance(type_, BlobType):
            statement.add("reader.get_bytes(reader.remaining)")
        elif isinstance(type_, StructType):
            statement.add(f"{type_.name}.deserialize(reader)").add_import_by_type(type_)
        else:
            raise AssertionError("Unhandled Type")

        if self._array_field:
            statement.add(")")

        return statement.add("\n")

    def _check_field_accessible(self, field):
        field_data = self._context.accessible_fields.get(field)
        if not field_data:
            raise RuntimeError(f'Referenced {field} field is not accessible.')

    def _get_serialize_length_expression(self):
        expression = self._length_string
        if expression is not None:
            if not expression.isdigit():
                self._check_field_accessible(expression)
                expression = f'data._{expression}'
        return expression

    def _get_deserialize_length_expression(self):
        expression = self._length_string
        if expression is not None:
            if not expression.isdigit():
                self._check_field_accessible(expression)
        return expression

    @staticmethod
    def _get_length_offset_expression(offset):
        if offset != 0:
            return f" {'+' if offset > 0 else '-'} {abs(offset)}"
        return None

    @staticmethod
    def _get_read_statement_for_basic_type(type_, length_expression, padded):
        if type_.name == "byte":
            return "reader.get_byte()"
        elif type_.name == "char":
            return "reader.get_char()"
        elif type_.name == "short":
            return "reader.get_short()"
        elif type_.name == "three":
            return "reader.get_three()"
        elif type_.name == "int":
            return "reader.get_int()"
        elif type_.name == "string":
            if length_expression is None:
                return "reader.get_string()"
            else:
                return f"reader.get_fixed_string({length_expression}, {padded})"
        elif type_.name == "encoded_string":
            if length_expression is None:
                return "reader.get_encoded_string()"
            else:
                return f"reader.get_fixed_encoded_string({length_expression}, {padded})"
        else:
            raise AssertionError("Unhandled BasicType")

    def _get_type(self):
        return self._type_factory.get_type(self._type_string, self._get_type_length())

    def _get_type_length(self):
        if self._array_field:
            return Length.unspecified()

        if self._length_string is not None:
            return Length.from_string(self._length_string)

        return Length.unspecified()

    def _get_python_type_name(self, field_type):
        if isinstance(field_type, IntegerType):
            return "int"

        if isinstance(field_type, StringType):
            return "str"

        if isinstance(field_type, BoolType):
            return "bool"

        if isinstance(field_type, BlobType):
            return "bytes"

        if isinstance(field_type, CustomType):
            return field_type.name

        raise AssertionError("Unhandled Type")


class FieldCodeGeneratorBuilder:
    def __init__(self, type_factory, context, data):
        self._type_factory = type_factory
        self._context = context
        self._data = data
        self._name = None
        self._type = None
        self._length = None
        self._offset = 0
        self._padded = False
        self._optional = False
        self._hardcoded_value = None
        self._comment = None
        self._array_field = False
        self._length_field = False
        self._delimited = False
        self._trailing_delimiter = False

    def name(self, name):
        self._name = name
        return self

    def type(self, type_str):
        self._type = type_str
        return self

    def length(self, length):
        self._length = length
        return self

    def padded(self, padded):
        self._padded = padded
        return self

    def optional(self, optional):
        self._optional = optional
        return self

    def hardcoded_value(self, hardcoded_value):
        self._hardcoded_value = hardcoded_value
        return self

    def comment(self, comment):
        self._comment = comment
        return self

    def array_field(self, array_field):
        self._array_field = array_field
        return self

    def delimited(self, delimited):
        self._delimited = delimited
        return self

    def trailing_delimiter(self, trailing_delimiter):
        self._trailing_delimiter = trailing_delimiter
        return self

    def length_field(self, length_field):
        self._length_field = length_field
        return self

    def offset(self, offset):
        self._offset = offset
        return self

    def build(self):
        if self._type is None:
            raise ValueError("type must be provided")
        return FieldCodeGenerator(
            self._type_factory,
            self._context,
            self._data,
            self._name,
            self._type,
            self._length,
            self._padded,
            self._optional,
            self._hardcoded_value,
            self._comment,
            self._array_field,
            self._delimited,
            self._trailing_delimiter,
            self._length_field,
            self._offset,
        )


def get_max_value_of(integer_type):
    return 255 if integer_type.name == 'byte' else pow(253, integer_type.fixed_size) - 1
