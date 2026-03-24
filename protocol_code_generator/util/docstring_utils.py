from html import escape

from protocol_code_generator.generate.code_block import CodeBlock


def _generate_docstring_from_lines(lines):
    result = CodeBlock()
    if lines:
        result.add('"""\n' + '\n'.join(lines) + '\n"""\n')
    return result


def _get_docstring_lines(text):
    if not text:
        return []
    return list(map(str.strip, escape(text, quote=False).split('\n')))


def generate_docstring(protocol_comment):
    return _generate_docstring_from_lines(_get_docstring_lines(protocol_comment))
