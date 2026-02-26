from abc import abstractmethod
from protocol_code_generator.type.type import Type


class CustomType(Type):
    @property
    @abstractmethod
    def source_path(self):
        pass
