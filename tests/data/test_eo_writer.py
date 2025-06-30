import pytest
from eolib.data.eo_numeric_limits import CHAR_MAX, SHORT_MAX, THREE_MAX, INT_MAX
from eolib.data.eo_writer import EoWriter


def test_add_byte():
    writer = EoWriter()
    writer.add_byte(0x00)
    assert writer.to_bytearray() == bytearray([0x00])


def test_add_bytes():
    writer = EoWriter()
    writer.add_bytes(bytes([0x00, 0xFF]))
    assert writer.to_bytearray() == bytearray([0x00, 0xFF])


def test_add_char():
    writer = EoWriter()
    writer.add_char(123)
    assert writer.to_bytearray() == bytearray([0x7C])


def test_add_short():
    writer = EoWriter()
    writer.add_short(12345)
    assert writer.to_bytearray() == bytearray([0xCA, 0x31])


def test_add_three():
    writer = EoWriter()
    writer.add_three(10000000)
    assert writer.to_bytearray() == bytearray([0xB0, 0x3A, 0x9D])


def test_add_int():
    writer = EoWriter()
    writer.add_int(2048576040)
    assert writer.to_bytearray() == bytearray([0x7F, 0x7F, 0x7F, 0x7F])


def test_add_string():
    writer = EoWriter()
    writer.add_string("foo")
    assert writer.to_bytearray() == b'foo'


def test_add_fixed_string():
    writer = EoWriter()
    writer.add_fixed_string("bar", 3)
    assert writer.to_bytearray() == b'bar'


def test_add_padded_fixed_string():
    writer = EoWriter()
    writer.add_fixed_string("bar", 6, True)
    assert writer.to_bytearray() == b'bar\xff\xff\xff'


def test_add_padded_with_perfect_fit_fixed_string():
    writer = EoWriter()
    writer.add_fixed_string("bar", 3, True)
    assert writer.to_bytearray() == b'bar'


def test_add_encoded_string():
    writer = EoWriter()
    writer.add_encoded_string("foo")
    assert writer.to_bytearray() == b'^0g'


def test_add_fixed_encoded_string():
    writer = EoWriter()
    writer.add_fixed_encoded_string("bar", 3)
    assert writer.to_bytearray() == b'[>k'


def test_add_padded_fixed_encoded_string():
    writer = EoWriter()
    writer.add_fixed_encoded_string("bar", 6, True)
    assert writer.to_bytearray() == b'\xff\xff\xff-l='


def test_add_padded_with_perfect_fit_fixed_encoded_string():
    writer = EoWriter()
    writer.add_fixed_encoded_string("bar", 3, True)
    assert writer.to_bytearray() == b'[>k'


def test_add_sanitized_string():
    writer = EoWriter()
    writer.string_sanitization_mode = True
    writer.add_string("aÿz")
    assert writer.to_bytearray() == b'ayz'


def test_add_sanitized_fixed_string():
    writer = EoWriter()
    writer.string_sanitization_mode = True
    writer.add_fixed_string("aÿz", 3)
    assert writer.to_bytearray() == b'ayz'


def test_add_sanitized_padded_fixed_string():
    writer = EoWriter()
    writer.string_sanitization_mode = True
    writer.add_fixed_string("aÿz", 6, True)
    assert writer.to_bytearray() == b'ayz\xff\xff\xff'


def test_add_sanitized_encoded_string():
    writer = EoWriter()
    writer.string_sanitization_mode = True
    writer.add_encoded_string("aÿz")
    assert writer.to_bytearray() == b'S&l'


def test_add_sanitized_fixed_encoded_string():
    writer = EoWriter()
    writer.string_sanitization_mode = True
    writer.add_fixed_encoded_string("aÿz", 3)
    assert writer.to_bytearray() == b'S&l'


def test_add_sanitized_padded_fixed_encoded_string():
    writer = EoWriter()
    writer.string_sanitization_mode = True
    writer.add_fixed_encoded_string("aÿz", 6, True)
    assert writer.to_bytearray() == b'\xff\xff\xff%T>'


def test_add_numbers_on_boundary():
    writer = EoWriter()
    writer.add_byte(0xFF)
    writer.add_char(CHAR_MAX - 1)
    writer.add_short(SHORT_MAX - 1)
    writer.add_three(THREE_MAX - 1)
    writer.add_int(INT_MAX - 1)


def test_add_numbers_exceeding_limit():
    writer = EoWriter()
    with pytest.raises(ValueError):
        writer.add_byte(256)
    with pytest.raises(ValueError):
        writer.add_char(256)
    with pytest.raises(ValueError):
        writer.add_short(65536)
    with pytest.raises(ValueError):
        writer.add_three(16777216)
    with pytest.raises(ValueError):
        writer.add_int(4294967296)


def test_add_fixed_string_with_incorrect_length():
    writer = EoWriter()
    with pytest.raises(ValueError):
        writer.add_fixed_string("foo", 2)
    with pytest.raises(ValueError):
        writer.add_fixed_string("foo", 2, True)
    with pytest.raises(ValueError):
        writer.add_fixed_string("foo", 4)
    with pytest.raises(ValueError):
        writer.add_fixed_encoded_string("foo", 2)
    with pytest.raises(ValueError):
        writer.add_fixed_encoded_string("foo", 2, True)
    with pytest.raises(ValueError):
        writer.add_fixed_encoded_string("foo", 4)


def test_get_string_sanitization_mode():
    writer = EoWriter()
    assert not writer.string_sanitization_mode
    writer.string_sanitization_mode = True
    assert writer.string_sanitization_mode


def test_len():
    writer = EoWriter()
    assert len(writer) == 0

    writer.add_string("Lorem ipsum dolor sit amet")
    assert len(writer) == 26

    for _ in range(27, 101):
        writer.add_byte(0xFF)
    assert len(writer) == 100
