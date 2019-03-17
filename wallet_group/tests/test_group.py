import pytest
from wallet_group.group import connect_input, env

class DB(object):

    def put(self, k, v):
        pass

def pprint():
    with env.begin(write=True) as txn:
        cursor = txn.cursor()
        for k, v in cursor:
            print(k, v)

@pytest.fixture
def db():
    yield DB()

def create_input(*args):
    res = []
    for arg in args:
        res.append('test_%s' % arg)
    return res

def test_group(db):
    connect_input(db, create_input(1))
    connect_input(db, create_input(1, 2))
    connect_input(db, create_input(2))
    connect_input(db, create_input(3, 2))
    connect_input(db, create_input(9, 8))
    connect_input(db, create_input(9, 1))
    pprint()
