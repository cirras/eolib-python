from abc import abstractmethod
from protocol_code_generator.type.type import Type


class HasUnderlyingType(Type):
    @property
    @abstractmethod
    def underlying_type(self):
        pass
