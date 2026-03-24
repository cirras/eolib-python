from .sequence_start import SequenceStart


class PacketSequencer:
    """A class for generating packet sequences."""

    _start: SequenceStart
    _counter: int

    def __init__(self, start: SequenceStart):
        """
        Constructs a new PacketSequencer with the provided SequenceStart.

        Args:
            start (SequenceStart): The sequence start.
        """
        self._start = start
        self._counter = 0

    def next_sequence(self) -> int:
        """
        Returns the next sequence value, updating the sequence counter in the process.

        Note:
            This is not a monotonic operation. The sequence counter increases from 0 to 9 before
            looping back around to 0.

        Returns:
            The next sequence value.
        """
        result = self._start.value + self._counter
        self._counter = (self._counter + 1) % 10
        return result

    def set_sequence_start(self, start: SequenceStart) -> None:
        """
        Sets the sequence start, also known as the "starting counter ID".

        Note:
            This does not reset the sequence counter.

        Args:
            start (SequenceStart): The new sequence start.
        """
        self._start = start
