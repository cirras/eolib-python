def interleave(data: bytearray) -> None:
    """
    Interleaves a sequence of bytes. When encrypting EO data, bytes are "woven" into each other.

    Used when encrypting packets and data files.

    Example:
        >>> interleave([0, 1, 2, 3, 4, 5])
        [0, 5, 1, 4, 2, 3]

    This is an in-place operation.

    Args:
        data (bytearray): The data to interleave.
    """
    buffer = bytearray(len(data))
    i = 0
    ii = 0

    while i < len(data):
        buffer[i] = data[ii]
        i += 2
        ii += 1

    i -= 1

    if len(data) % 2 != 0:
        i -= 2

    while i >= 0:
        buffer[i] = data[ii]
        i -= 2
        ii += 1

    data[:] = buffer


def deinterleave(data: bytearray) -> None:
    """
    Deinterleaves a sequence of bytes. This is the reverse of interleave.

    Used when decrypting packets and data files.

    Example:
        >>> deinterleave([0, 1, 2, 3, 4, 5])
        [0, 2, 4, 5, 3, 1]

    This is an in-place operation.

    Args:
        data (bytearray): The data to deinterleave.
    """
    buffer = bytearray(len(data))
    i = 0
    ii = 0

    while i < len(data):
        buffer[ii] = data[i]
        i += 2
        ii += 1

    i -= 1

    if len(data) % 2 != 0:
        i -= 2

    while i >= 0:
        buffer[ii] = data[i]
        i -= 2
        ii += 1

    data[:] = buffer


def flip_msb(data: bytearray) -> None:
    """
    Flips the most significant bits of each byte in a sequence of bytes.
    (Values 0 and 128 are not flipped.)

    Used when encrypting and decrypting packets.

    Example:
        >>> flip_msb([0, 1, 127, 128, 129, 254, 255])
        [0, 129, 255, 128, 1, 126, 127]

    This is an in-place operation.

    Args:
        data (bytearray): The data to flip most significant bits on.
    """
    for i in range(len(data)):
        if data[i] & 0x7F != 0:
            data[i] = data[i] ^ 0x80


def swap_multiples(data: bytearray, multiple: int) -> None:
    """
    Swaps the order of contiguous bytes in a sequence of bytes that are divisible by a given
    multiple value.

    Used when encrypting and decrypting packets and data files.

    Example:
        >>> swap_multiples([10, 21, 27], 3)
        [10, 27, 21]

    This is an in-place operation.

    Args:
        data (bytearray): The data to swap bytes in.
        multiple (int): The multiple value.
    Raises:
        ValueError: If multiple is less than 1.
    """
    if multiple < 0:
        raise ValueError("multiple must be a positive number")

    if multiple == 0:
        return

    sequence_length = 0

    for i in range(len(data) + 1):
        if i != len(data) and data[i] % multiple == 0:
            sequence_length += 1
        else:
            if sequence_length > 1:
                for ii in range(sequence_length // 2):
                    b = data[i - sequence_length + ii]
                    data[i - sequence_length + ii] = data[i - ii - 1]
                    data[i - ii - 1] = b

            sequence_length = 0
