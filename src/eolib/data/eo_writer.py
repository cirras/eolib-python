from eolib.data.eo_numeric_limits import CHAR_MAX, SHORT_MAX, THREE_MAX, INT_MAX
from eolib.data.number_encoding_utils import encode_number
from eolib.data.string_encoding_utils import encode_string


class EoWriter:
    """
    A class for writing EO data to a sequence of bytes.
    """

    def __init__(self):
        """
        Creates a new ``EoWriter`` with no data.
        """
        self.data = bytearray()
        self._string_sanitization_mode = False

    def add_byte(self, value: int) -> None:
        """
        Adds a raw byte to the writer data.

        Args:
            value (int): The byte to add.

        Raises:
            ValueError: If the value is above `0xFF`.
        """
        self._check_number_size(value, 0xFF)
        self.data.append(value)

    def add_bytes(self, bytes: bytes) -> None:
        """
        Adds raw bytes to the writer data.

        Args:
            bytes (bytes): The bytes to add.
        """
        self.data.extend(bytes)

    def add_char(self, number: int) -> None:
        """
        Adds an encoded 1-byte integer to the writer data.

        Args:
            number (int): The number to encode and add.

        Raises:
            ValueError: If the value is not below `CHAR_MAX`.
        """
        self._check_number_size(number, CHAR_MAX - 1)
        number_bytes = encode_number(number)
        self._add_bytes_with_length(number_bytes, 1)

    def add_short(self, number: int) -> None:
        """
        Adds an encoded 2-byte integer to the writer data.

        Args:
            number (int): The number to encode and add.

        Raises:
            ValueError: If the value is not below `SHORT_MAX`.
        """
        self._check_number_size(number, SHORT_MAX - 1)
        number_bytes = encode_number(number)
        self._add_bytes_with_length(number_bytes, 2)

    def add_three(self, number: int) -> None:
        """
        Adds an encoded 3-byte integer to the writer data.

        Args:
            number (int): The number to encode and add.

        Raises:
            ValueError: If the value is not below `THREE_MAX`.
        """
        self._check_number_size(number, THREE_MAX - 1)
        number_bytes = encode_number(number)
        self._add_bytes_with_length(number_bytes, 3)

    def add_int(self, number: int) -> None:
        """
        Adds an encoded 4-byte integer to the writer data.

        Args:
            number (int): The number to encode and add.

        Raises:
            ValueError: If the value is not below `INT_MAX`.
        """
        self._check_number_size(number, INT_MAX - 1)
        number_bytes = encode_number(number)
        self._add_bytes_with_length(number_bytes, 4)

    def add_string(self, string: str) -> None:
        """
        Adds a string to the writer data.

        Args:
            string (str): The string to be added.
        """
        string_bytes = self._encode_ansi(string)
        self._sanitize_string(string_bytes)
        self.add_bytes(string_bytes)

    def add_fixed_string(self, string: str, length: int, padded: bool = False) -> None:
        """
        Adds a fixed-length string to the writer data.

        Args:
            string (str): The string to be added.
            length (int): The expected length of the string.
            padded (bool, optional): True if the string should be padded to the length with
                trailing `0xFF` bytes. Defaults to False.
        """
        self._check_string_length(string, length, padded)
        string_bytes = self._encode_ansi(string)
        self._sanitize_string(string_bytes)
        if padded:
            string_bytes = self._add_padding(string_bytes, length)
        self.add_bytes(string_bytes)

    def add_encoded_string(self, string: str) -> None:
        """
        Adds an encoded string to the writer data.

        Args:
            string (str): The string to be encoded and added.
        """
        string_bytes = self._encode_ansi(string)
        self._sanitize_string(string_bytes)
        encode_string(string_bytes)
        self.add_bytes(string_bytes)

    def add_fixed_encoded_string(self, string: str, length: int, padded: bool = False) -> None:
        """
        Adds a fixed-length encoded string to the writer data.

        Args:
            string (str): The string to be encoded and added.
            length (int): The expected length of the string.
            padded (bool, optional): True if the string should be padded to the length with
                trailing `0xFF` bytes. Defaults to False.
        """
        self._check_string_length(string, length, padded)
        string_bytes = self._encode_ansi(string)
        self._sanitize_string(string_bytes)
        if padded:
            string_bytes = self._add_padding(string_bytes, length)
        encode_string(string_bytes)
        self.add_bytes(string_bytes)

    @property
    def string_sanitization_mode(self) -> bool:
        """
        Whether string sanitization is enabled for the writer.
        """
        return self._string_sanitization_mode

    @string_sanitization_mode.setter
    def string_sanitization_mode(self, string_sanitization_mode: bool) -> None:
        self._string_sanitization_mode = string_sanitization_mode

    def to_bytearray(self) -> bytearray:
        """
        Gets the writer data as a byte array.

        Returns:
            A copy of the writer data as a byte array.
        """
        return self.data.copy()

    def __len__(self) -> int:
        """
        Gets the length of the writer data.

        Returns:
            The length of the writer data.
        """
        return len(self.data)

    def _add_bytes_with_length(self, bytes: bytes, bytes_length: int) -> None:
        """
        Adds raw bytes with a specified length to the writer data.

        Args:
            bytes (bytes): The bytes to add.
            bytes_length (int): The number of bytes to add.
        """
        self.data.extend(bytes[:bytes_length])

    def _sanitize_string(self, bytes: bytearray) -> None:
        if self.string_sanitization_mode:
            for i in range(len(bytes)):
                if bytes[i] == 0xFF:  # 'ÿ'
                    bytes[i] = 0x79  # 'y'

    @staticmethod
    def _check_number_size(number: int, max_value: int) -> None:
        if number > max_value:
            raise ValueError(f"Value {number} exceeds maximum of {max_value}.")

    @staticmethod
    def _add_padding(bytes: bytearray, length: int) -> bytearray:
        if len(bytes) == length:
            return bytes

        result = bytearray(length)
        result[: len(bytes)] = bytes
        result[len(bytes) :] = bytearray([0xFF] * (length - len(bytes)))

        return result

    @staticmethod
    def _check_string_length(string: str, length: int, padded: bool) -> None:
        if padded:
            if length >= len(string):
                return
            raise ValueError(f'Padded string "{string}" is too large for a length of {length}.')

        if len(string) != length:
            raise ValueError(f'String "{string}" does not have expected length of {length}.')

    @staticmethod
    def _encode_ansi(string: str) -> bytearray:
        """
        Encodes string to windows-1252 bytes.

        Args:
            string (str): The string to encode.

        Returns:
            The encoded string.
        """
        return bytearray(string, 'windows-1252', 'replace')
