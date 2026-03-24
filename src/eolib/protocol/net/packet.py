from abc import ABC, abstractmethod

from eolib.data.eo_writer import EoWriter
from eolib.protocol._generated.net.packet_family import PacketFamily
from eolib.protocol._generated.net.packet_action import PacketAction


class Packet(ABC):
    """
    Object representation of a packet in the EO network protocol.
    """

    @staticmethod
    @abstractmethod
    def family() -> PacketFamily:
        """
        Returns the packet family associated with this packet.

        Returns:
            The packet family associated with this packet.
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def action() -> PacketAction:
        """
        Returns the packet action associated with this packet.

        Returns:
            The packet action associated with this packet.
        """
        raise NotImplementedError()

    @abstractmethod
    def write(self, writer: EoWriter) -> None:
        """
        Serializes and writes this packet to the provided EoWriter.

        Args:
            writer (EoWriter): the writer that this packet will be written to.
        """
        raise NotImplementedError()
