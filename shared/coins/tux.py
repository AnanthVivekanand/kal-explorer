import bitcointx
from bitcointx.core import CBlock
from shared.utils import x

COIN = 100000000

class ChainParams(bitcointx.core.CoreChainParams):
    MAX_MONEY = 69000000 * COIN
    GENESIS_BLOCK = CBlock.deserialize(x('010000000000000000000000000000000000000000000000000000000000000000000000bbd46d60742caabc880e7374621c730cf1b6ddb5c76583fc9b8fad233510ad3e5cb0255bf0ff0f1eeed74e7c0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4e04ffff001d0104464e6f727468204b6f7265616e2066696c6d206f6e204b696d27732053696e6761706f726520747269702072657665616c73206e657720666f637573206f6e2065636f6e6f6d79ffffffff0100a5459b0100000043410476929ca6904b40d59cc9af2907a050d5b8f332111b83aebfd6258a68dfb771895c96c1eeac808aeb083f5ec54a44dd282a6b34944fce8726c1980c1f06a6b69eac00000000'))
    PROOF_OF_WORK_LIMIT = None # currently not needed
    SUBSIDY_HALVING_INTERVAL = 469000 # currently not needed
    NAME = 'mainnet' # currently not needed
    RPC_PORT = 42072
    PORT = 42071
    NETMAGIC = b'\xfc\xc5\xbf\xda'
    BASE58_PREFIXES = {
        'PUBKEY_ADDR':65,
        'SCRIPT_ADDR':64,
        'SECRET_KEY' :193,
        'EXTENDED_PUBKEY': b'\x04\x88\xb2\x1e',
        'EXTENDED_PRIVKEY': b'\x04\x88\xad\xe4'
    }
    BECH32_HRP = 'tux'


PROTO_VERSION = 70002
MIN_PROTO_VERSION = 70002
CADDR_TIME_VERSION = 31402
NOBLKS_VERSION_START = 60002
BIP0031_VERSION = 60000

POOLS = {
    'blazepool': {
        'name': 'BlazePool',
        'url': 'http://blazepool.com'
    },
    'zpool.ca': {
        'name': 'Zpool',
        'url': 'https://zpool.ca'
    },
    'zerg': {
        'name': 'Zerg Pool',
        'url': 'http://zergpool.com/'
    },
    'ahashpool': {
        'name': 'A Hash Pool',
        'url': 'https://www.ahashpool.com/'
    },
    'tuxtoke.life': {
        'name': 'Tuxtoke',
        'url': 'http://pool.tuxtoke.life'
    }
}
