from enum import EnumMeta


class ProtocolEnumMeta(EnumMeta):
    """
    Enum metaclass that preserves unrecognized values as synthetic enum members.
    """

    def __call__(cls, value, names=None, *, module=None, qualname=None, type=None, start=1):
        if names is not None:
            return super().__call__(
                value, names=names, module=module, qualname=qualname, type=type, start=start
            )
        try:
            return super().__call__(value, module=module, qualname=qualname, type=type, start=start)
        except ValueError:
            unrecognized = int.__new__(cls, value)
            unrecognized._name_ = f"Unrecognized({int(value)})"
            unrecognized._value_ = value
            return unrecognized
