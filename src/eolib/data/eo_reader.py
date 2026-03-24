from typing import Optional
from eolib.data.number_encoding_utils import decode_number
from eolib.data.string_encoding_utils import decode_string


class EoReader(object):
    """
    A class for reading EO data from a sequence of bytes.

    ``EoReader`` features a chunked reading mode, which is important for accurate emulation of
    the official game client.

    See the `chunked reading documentation
    <https://github.com/Cirras/eo-protocol/blob/master/docs/chunks.md>`_ for more information.
    """

    _data: memoryview
    _position: int
    _chunked_reading_mode: bool
    _chunk_start: int
    _next_break: int

    def __init__(self, data: bytes):
        """
        Creates a new `EoReader` instance for the specified data.

        Args:
            data (bytes): The byte array containing the input data.
        """
        self._data = memoryview(data)
        self._position = 0
        self._chunked_reading_mode = False
        self._chunk_start = 0
        self._next_break = -1

    def slice(self, index: Optional[int] = None, length: Optional[int] = None) -> "EoReader":
        """
        Creates a new `EoReader` whose input data is a shared subsequence of this reader's
        data.

        The input data of the new reader will start at position `index` in this reader and contain
        up to `length` bytes. The two reader's position and chunked reading mode will be
        independent.

        The new reader's position will be zero, and its chunked reading mode will be false.

        Args:
            index (int, optional): The position in this reader at which the data of the new reader
                will start; must be non-negative. Defaults to the current reader position.
            length (int, optional): The length of the shared subsequence of data to supply to the
                new reader; must be non-negative. Defaults to the length of the remaining data
                starting from `index`.

        Returns:
            The new reader.

        Raises:
            ValueError: If `index` or `length` is negative.
        """
        if index is None:
            index = self.position
        if length is None:
            length = max(0, len(self._data) - index)

        if index < 0:
            raise ValueError(f"negative index: {index}")

        if length < 0:
            raise ValueError(f"negative length: {length}")

        begin = max(0, min(len(self._data), index))
        end = begin + min(len(self._data) - begin, length)

        return EoReader(self._data[begin:end])

    def get_byte(self) -> int:
        """
        Reads a raw byte from the input data.

        Returns:
            A raw byte.
        """
        return self._read_byte()

    def get_bytes(self, length: int) -> bytearray:
        """
        Reads an array of raw bytes from the input data.

        Args:
            length (int): The number of bytes to read.

        Returns:
            An array of raw bytes.
        """
        return self._read_bytes(length)

    def get_char(self) -> int:
        """
        Reads an encoded 1-byte integer from the input data.

        Returns:
            A decoded 1-byte integer.
        """
        return decode_number(self._read_bytes(1))

    def get_short(self) -> int:
        """
        Reads an encoded 2-byte integer from the input data.

        Returns:
            A decoded 2-byte integer.
        """
        return decode_number(self._read_bytes(2))

    def get_three(self) -> int:
        """
        Reads an encoded 3-byte integer from the input data.

        Returns:
            A decoded 3-byte integer.
        """
        return decode_number(self._read_bytes(3))

    def get_int(self) -> int:
        """
        Reads an encoded 4-byte integer from the input data.

        Returns:
            A decoded 4-byte integer.
        """
        return decode_number(self._read_bytes(4))

    def get_string(self) -> str:
        """
        Reads a string from the input data.

        Returns:
            A string.
        """
        string_bytes = self._read_bytes(self.remaining)
        return self._decode_ansi(string_bytes)

    def get_fixed_string(self, length: int, padded: bool = False) -> str:
        """
        Reads a string with a fixed length from the input data.

        Args:
            length (int): The length of the string.
            padded (bool, optional): True if the string is padded with trailing `0xFF` bytes.

        Returns:
            A decoded string.

        Raises:
            ValueError: If the length is negative.
        """
        if length < 0:
            raise ValueError("Negative length")
        bytes_ = self._read_bytes(length)
        if padded:
            bytes_ = self._remove_padding(bytes_)
        return self._decode_ansi(bytes_)

    def get_encoded_string(self) -> str:
        """
        Reads an encoded string from the input data.

        Returns:
            A decoded string.
        """
        bytes_ = self._read_bytes(self.remaining)
        decode_string(bytes_)
        return self._decode_ansi(bytes_)

    def get_fixed_encoded_string(self, length: int, padded: bool = False) -> str:
        """
        Reads an encoded string with a fixed length from the input data.

        Args:
            length (int): The length of the string.
            padded (bool, optional): True if the string is padded with trailing `0xFF` bytes.

        Returns:
            A decoded string.

        Raises:
            ValueError: If the length is negative.
        """
        if length < 0:
            raise ValueError("Negative length")
        bytes_ = self._read_bytes(length)
        decode_string(bytes_)
        if padded:
            bytes_ = self._remove_padding(bytes_)
        return self._decode_ansi(bytes_)

    @property
    def chunked_reading_mode(self) -> bool:
        """
        Gets or sets the chunked reading mode for the reader.

        In chunked reading mode:

        - The reader will treat ``0xFF`` bytes as the end of the current chunk.
        - :meth:`next_chunk` can be called to move to the next chunk.
        """
        return self._chunked_reading_mode

    @chunked_reading_mode.setter
    def chunked_reading_mode(self, chunked_reading_mode: bool) -> None:
        self._chunked_reading_mode = chunked_reading_mode
        if self._next_break == -1:
            self._next_break = self._find_next_break_index()

    @property
    def remaining(self) -> int:
        """
        If chunked reading mode is enabled, gets the number of bytes remaining in the current
        chunk. Otherwise, gets the total number of bytes remaining in the input data.
        """
        if self.chunked_reading_mode:
            return self._next_break - min(self.position, self._next_break)
        else:
            return len(self._data) - self.position

    def next_chunk(self) -> None:
        """
        Moves the reader position to the start of the next chunk in the input data.

        Raises:
            RuntimeError: If not in chunked reading mode.
        """
        if not self.chunked_reading_mode:
            raise RuntimeError("Not in chunked reading mode.")

        self._position = self._next_break
        if self._position < len(self._data):
            # Skip the break byte
            self._position += 1

        self._chunk_start = self._position
        self._next_break = self._find_next_break_index()

    @property
    def position(self) -> int:
        """
        Gets the current position in the input data.
        """
        return self._position

    def _read_byte(self) -> int:
        """
        Reads a raw byte from the input data.

        Returns:
            A raw byte.
        """
        if self.remaining > 0:
            byte = self._data[self._position]
            self._position += 1
            return byte
        return 0

    def _read_bytes(self, length) -> bytearray:
        """
        Reads an array of raw bytes from the input data.

        Args:
            length (int): The number of bytes to read.

        Returns:
            An array of raw bytes.
        """
        length = min(length, self.remaining)

        result = bytearray(self._data[self._position : self._position + length])
        self._position += length

        return result

    def _find_next_break_index(self) -> int:
        """
        Finds the index of the next break byte (0xFF) in the input data.

        Returns:
            The index of the next break byte, or the length of the data if not found.
        """
        for i in range(self._chunk_start, len(self._data)):
            if self._data[i] == 0xFF:
                return i
        return len(self._data)

    @staticmethod
    def _remove_padding(array: bytearray) -> bytearray:
        """
        Removes padding (trailing 0xFF bytes) from a sequence of bytes.

        Args:
            array (bytearray): The sequence of bytes.

        Returns:
            The bytes without padding.
        """
        padding_start = array.find(bytes([0xFF]))
        if padding_start != -1:
            return array[:padding_start]
        return array

    @staticmethod
    def _decode_ansi(bytes: bytearray) -> str:
        """
        Decodes windows-1252 bytes to a string.

        Args:
            bytes (bytearray): The sequence of bytes to decode.

        Returns:
            The decoded string.
        """
        return bytes.decode('windows-1252', 'replace')
