from abc import ABC, abstractmethod


class Type(ABC):
    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def fixed_size(self):
        pass

    @property
    @abstractmethod
    def bounded(self):
        pass
