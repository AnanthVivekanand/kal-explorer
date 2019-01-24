from peewee import *
from playhouse.postgres_ext import BinaryJSONField

db = PostgresqlDatabase('tuxcoin', user='postgres', password='postgres', host='localhost', port=5432)

class BaseModel(Model):
	class Meta:
		database = db

class Block(BaseModel):
	height = IntegerField(unique=True)
	hash = CharField(max_length=64, unique=True)
	timestamp = DateTimeField()
	merkle_root = CharField(max_length=64, unique=True)
	tx = BinaryJSONField()
	difficulty = FloatField()
	size = IntegerField()
	version = BlobField()
	bits = BlobField()
	nonce = BigIntegerField()
	coinbase = BlobField()
	tx_count = IntegerField()


class Transaction(BaseModel):
	txid = CharField(max_length=64, unique=True, index=True)
	block = CharField(max_length=64, null=True)
	block_height = IntegerField(null=True)
	timestamp = DateTimeField()
	vin = BinaryJSONField()
	addresses_in = BinaryJSONField()
	addresses_out = BinaryJSONField()
	vout = BinaryJSONField()
	input_value = BigIntegerField()
	output_value = BigIntegerField()

class Message(BaseModel):
	message = TextField()

class AddressChanges(BaseModel):
	address = TextField(index=True)
	balance_change = BigIntegerField()

class Address(BaseModel):
	address = TextField(unique=True, index=True)
	balance = BigIntegerField()

db.connect()
db.drop_tables([Block, Transaction, Address, AddressChanges, Message])
db.create_tables([Block, Transaction, Address, AddressChanges, Message])
