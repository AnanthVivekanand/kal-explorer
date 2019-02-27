import binascii

def x(h):
    """Convert a hex string to bytes"""
    return binascii.unhexlify(h.encode('utf8'))