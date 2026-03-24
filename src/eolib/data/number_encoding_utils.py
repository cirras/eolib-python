from eolib.data.eo_numeric_limits import CHAR_MAX, SHORT_MAX, THREE_MAX


def encode_number(number: int) -> bytes:
    """
    Encodes a number to a sequence of bytes.

    Args:
        number (int): The number to encode.

    Returns:
        The encoded sequence of bytes.
    """
    value = number
    d = 0xFE
    if number >= THREE_MAX:
        d = value // THREE_MAX + 1
        value = value % THREE_MAX

    c = 0xFE
    if number >= SHORT_MAX:
        c = value // SHORT_MAX + 1
        value = value % SHORT_MAX

    b = 0xFE
    if number >= CHAR_MAX:
        b = value // CHAR_MAX + 1
        value = value % CHAR_MAX

    a = value + 1

    return bytes([a, b, c, d])


def decode_number(encoded_number: bytes) -> int:
    """
    Decodes a number from a sequence of bytes.

    Args:
        encoded_number (bytes): The sequence of bytes to decode.

    Returns:
        The decoded number.
    """
    result = 0
    length = min(len(encoded_number), 4)

    for i in range(length):
        value = encoded_number[i]

        if value == 0xFE:
            break

        value -= 1

        if i == 0:
            result += value
        elif i == 1:
            result += CHAR_MAX * value
        elif i == 2:
            result += SHORT_MAX * value
        elif i == 3:
            result += THREE_MAX * value

    return result
