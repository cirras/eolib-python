import pytest
from collections import namedtuple
from eolib.encrypt.encryption_utils import interleave, deinterleave, flip_msb, swap_multiples

TCase = namedtuple("TCase", ["string", "expected"])


def idfn(test_case: TCase) -> str:
    return test_case.string


@pytest.mark.parametrize(
    "test_case",
    [
        TCase("Hello, World!", "H!edlllroo,W "),
        TCase(
            "We're ¼ of the way there, so ¾ is remaining.",
            "W.eg'nrien i¼a moefr  tshie  ¾w aoys  t,heer",
        ),
        TCase("64² = 4096", "6649²0 4= "),
        TCase("© FÒÖ BÃR BÅZ 2014", "©4 1F0Ò2Ö  ZBÅÃBR "),
        TCase("Öxxö Xööx \"Lëïth Säë\" - \"Ÿ\"", "Ö\"xŸx\"ö  -X ö\"öëxä S\" Lhëtï"),
        TCase("Padded with 0xFFÿÿÿÿÿÿÿÿ", "Pÿaÿdÿdÿeÿdÿ ÿwÿiFtFhx 0"),
        TCase(
            "This string contains NUL\0 (value 0) and a € (value 128)",
            "T)h8i2s1  seturlianvg(  c€o nat adinnas  )N0U Le\0u l(av",
        ),
    ],
    ids=idfn,
)
def test_interleave(test_case: TCase):
    bytes_data = bytearray(test_case.string, 'windows-1252')
    interleave(bytes_data)
    result = bytes_data.decode('windows-1252')
    assert result == test_case.expected


@pytest.mark.parametrize(
    "test_case",
    [
        TCase("Hello, World!", "Hlo ol!drW,le"),
        TCase(
            "We're ¼ of the way there, so ¾ is remaining.",
            "W'e¼o h a hr,s  srmiig.nnae i¾o eetywetf  re",
        ),
        TCase("64² = 4096", "6²=4960  4"),
        TCase("© FÒÖ BÃR BÅZ 2014", "©FÖBRBZ2140 Å Ã Ò "),
        TCase("Öxxö Xööx \"Lëïth Säë\" - \"Ÿ\"", "Öx öx\"ët ä\"-\"\"Ÿ  ëShïL öXöx"),
        TCase("Padded with 0xFFÿÿÿÿÿÿÿÿ", "Pde ih0FÿÿÿÿÿÿÿÿFx twdda"),
        TCase(
            "This string contains NUL\0 (value 0) and a € (value 128)",
            "Ti tigcnan U\0(au )ada€(au 2)81elv   n 0elv LNsito nrssh",
        ),
    ],
    ids=idfn,
)
def test_deinterleave(test_case: TCase):
    bytes_data = bytearray(test_case.string, 'windows-1252')
    deinterleave(bytes_data)
    result = bytes_data.decode('windows-1252')
    assert result == test_case.expected


@pytest.mark.parametrize(
    "test_case",
    [
        TCase("Hello, World!", "Èåììï¬\u00a0×ïòìä¡"),
        TCase(
            "We're ¼ of the way there, so ¾ is remaining.",
            "×å§òå\u00a0<\u00a0ïæ\u00a0ôèå\u00a0÷áù\u00a0ôèåòå¬\u00a0óï\u00a0>\u00a0éó\u00a0òåíáéîéîç®",
        ),
        TCase("64² = 4096", "¶´2\u00a0½\u00a0´°¹¶"),
        TCase("© FÒÖ BÃR BÅZ 2014", ")\u00a0ÆRV\u00a0ÂCÒ\u00a0ÂEÚ\u00a0²°±´"),
        TCase(
            "Öxxö Xööx \"Lëïth Säë\" - \"Ÿ\"",
            "Vøøv\u00a0Øvvø\u00a0¢Ìkoôè\u00a0Ódk¢\u00a0\u00ad\u00a0¢\u001f¢",
        ),
        TCase(
            "Padded with 0xFFÿÿÿÿÿÿÿÿ",
            "Ðáääåä\u00a0÷éôè\u00a0°øÆÆ\u007f\u007f\u007f\u007f\u007f\u007f\u007f\u007f",
        ),
        TCase(
            "This string contains NUL\0 (value 0) and a € (value 128)",
            "Ôèéó\u00a0óôòéîç\u00a0ãïîôáéîó\u00a0ÎÕÌ\0\u00a0¨öáìõå\u00a0°©\u00a0áîä\u00a0á\u00a0€\u00a0¨öáìõå\u00a0±²¸©",
        ),
    ],
    ids=idfn,
)
def test_flip_msb(test_case: TCase):
    bytes_data = bytearray(test_case.string, 'windows-1252')
    flip_msb(bytes_data)
    result = bytes_data.decode('windows-1252')
    assert result == test_case.expected


@pytest.mark.parametrize(
    "test_case",
    [
        TCase("Hello, World!", "Heoll, lroWd!"),
        TCase(
            "We're ¼ of the way there, so ¾ is remaining.",
            "Wer'e ¼ fo the way there, so ¾ is remaining.",
        ),
        TCase("64² = 4096", "64² = 4690"),
        TCase("© FÒÖ BÃR BÅZ 2014", "© FÒÖ ÃBR BÅZ 2014"),
        TCase("Öxxö Xööx \"Lëïth Säë\" - \"Ÿ\"", "Ööxx Xxöö \"Lëïth Säë\" - \"Ÿ\""),
        TCase("Padded with 0xFFÿÿÿÿÿÿÿÿ", "Padded with x0FFÿÿÿÿÿÿÿÿ"),
        TCase(
            "This string contains NUL\0 (value 0) and a € (value 128)",
            "This stirng ocntains NUL\0 (vaule 0) and a € (vaule 128)",
        ),
    ],
    ids=idfn,
)
def test_swap_multiples(test_case: TCase):
    bytes_data = bytearray(test_case.string, 'windows-1252')
    swap_multiples(bytes_data, 3)
    result = bytes_data.decode('windows-1252')
    assert result == test_case.expected


def test_swap_multiples_with_zero_multiple_should_not_change_data():
    string = "Hello, World!"
    bytes_data = bytearray(string, 'windows-1252')
    swap_multiples(bytes_data, 0)
    result = bytes_data.decode('windows-1252')
    assert result == string


def test_swap_multiples_with_negative_multiple_should_throw():
    with pytest.raises(ValueError):
        swap_multiples(bytearray([1, 2, 3, 4, 5]), -1)
