import os
from collections import namedtuple


from protocol_code_generator.util.name_utils import pascal_case_to_snake_case


class Import:
    def __init__(self, import_name, absolute_package_path):
        self._import_name = import_name
        self._absolute_package_path = absolute_package_path

    def relativize(self, package_path):
        from_package_path = self._absolute_package_path

        if self._absolute_package_path.startswith('eolib.'):
            absolute_parts = self._absolute_package_path.split('.')
            base_parts = package_path.split('.')
            for _ in range(min(len(absolute_parts), len(base_parts))):
                if absolute_parts[0] == base_parts[0]:
                    absolute_parts.pop(0)
                    base_parts.pop(0)
                else:
                    break
            from_package_path = ('.' * (len(base_parts) + 1)) + '.'.join(absolute_parts)

        return f"from {from_package_path} import {self._import_name}"


class CodeBlock:
    def __init__(self):
        self._imports = set()
        self._lines = [""]
        self._indentation = 0

    def add(self, code):
        parts = code.split("\n")
        for i in range(len(parts)):
            if len(parts[i]) > 0:
                line_index = len(self._lines) - 1
                if len(self._lines[line_index]) == 0:
                    self._lines[line_index] = " " * (self._indentation * 4)
                self._lines[line_index] += parts[i]
            if i != len(parts) - 1:
                self._lines.append("")
        return self

    def add_line(self, line=""):
        self.add(f"{line}\n")
        return self

    def add_code_block(self, block):
        for i in block._imports:
            self._imports.add(i)

        for i in range(len(block._lines)):
            if i == len(block._lines) - 1:
                self.add(block._lines[i])
            else:
                self.add_line(block._lines[i])

        return self

    def add_import(self, import_name, absolute_package_path):
        self._imports.add(Import(import_name, absolute_package_path))
        return self

    def add_import_by_type(self, custom_type):
        relative_path = custom_type.source_path.replace('/', '.').lstrip('.')
        if relative_path:
            relative_path += '.'
        path = (
            'eolib.protocol._generated.'
            + relative_path
            + pascal_case_to_snake_case(custom_type.name)
        )
        self.add_import(custom_type.name, path)
        return self

    def begin_control_flow(self, control_flow):
        self.add_line(f"{control_flow}:")
        self.indent()
        return self

    def next_control_flow(self, control_flow):
        self.unindent()
        return self.begin_control_flow(control_flow)

    def indent(self):
        self._indentation += 1
        return self

    def unindent(self):
        self._indentation -= 1
        return self

    @property
    def empty(self):
        return len(self._lines) == 1 and len(self._lines[0]) == 0

    def __bool__(self):
        return not self.empty

    def to_string(self, package_path):
        result = ""

        import_strings = {i.relativize(package_path) for i in self._imports}
        import_strings = sorted(import_strings, reverse=True)

        for import_ in import_strings:
            if import_.startswith("from __future__"):
                import_strings.remove(import_)
                import_strings.insert(0, import_)

        for import_ in import_strings:
            result += import_ + "\n"

        if not self.empty:
            if len(result) > 0:
                result += "\n"

            result += "\n".join(self._lines)

        return result
