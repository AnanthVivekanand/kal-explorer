import binascii

def x(h):
    """Convert a hex string to bytes"""
    return binascii.unhexlify(h.encode('utf8'))

def bytes_to_int(b: bytes, *, signed: bool = False) -> int:
    return int.from_bytes(b, byteorder='big', signed=signed)