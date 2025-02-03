from html import escape

from protocol_code_generator.generate.code_block import CodeBlock


def generate_docstring(protocol_comment, notes=[]):
    lines = []

    if protocol_comment:
        lines.extend(map(str.strip, escape(protocol_comment, quote=False).split('\n')))

    result = CodeBlock()
    if lines:
        result.add('"""\n' + '\n'.join(lines) + '\n"""\n')

    return result
