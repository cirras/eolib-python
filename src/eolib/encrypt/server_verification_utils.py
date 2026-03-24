def server_verification_hash(challenge: int) -> int:
    """
    This hash function is used by the game client to verify communication with a genuine server
    during connection initialization.

    Args:
        challenge (int): The challenge value sent by the client.
                         Should be no larger than 11,092,110.

    Returns:
        The hashed challenge value.

    .. admonition:: Remarks

       - The client sends an integer value to the server in the ``INIT_INIT`` client packet, where
         it is referred to as the ``challenge``.
       - The server hashes the value and sends the hash back in the ``INIT_INIT`` server packet.
       - The client hashes the value and compares it to the hash sent by the server.
       - If the hashes do not match, the client drops the connection.

    .. warning::

       Oversized challenges may result in negative hash values, which cannot be represented
       properly in the EO protocol.

    .. seealso::

       - :attr:`eolib.protocol.net.client.InitInitClientPacket.challenge`
       - :attr:`eolib.protocol.net.server.InitInitServerPacket.ReplyCodeDataOk.challenge_response`
    """
    challenge += 1
    return (
        110905
        + (_mod(challenge, 9) + 1) * _mod(11092004 - challenge, ((challenge % 11) + 1) * 119) * 119
        + _mod(challenge, 2004)
    )


def _mod(a, b):
    result = a % b
    if a < 0:
        result -= b
    return result
