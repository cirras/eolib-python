from enum import IntEnum
from eolib import ProtocolEnumMeta


class ProtocolEnum(IntEnum, metaclass=ProtocolEnumMeta):
    FOO = 0
    BAR = 1
    BAZ = 2


def test_known_value():
    assert ProtocolEnum(0) is ProtocolEnum.FOO
    assert ProtocolEnum(1) is ProtocolEnum.BAR
    assert ProtocolEnum(2) is ProtocolEnum.BAZ


def test_unrecognized_value():
    unrecognized = ProtocolEnum(3)
    assert isinstance(unrecognized, ProtocolEnum)
    assert unrecognized.name == "Unrecognized(3)"
    assert unrecognized.value == 3
