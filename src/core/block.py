import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List

from .transaction import Transaction

GENESIS_HASH = "816534932c2b7154836da6afc367695e6337db8a921823784c14378abed4f7d7"
POW_DIFFICULTY = "000"


@dataclass
class Block:
    index: int
    previous_hash: str
    transactions: List[Transaction]
    nonce: int = 0
    timestamp: float = field(default_factory=time.time)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_data = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce,
            "timestamp": self.timestamp,
        }
        block_str = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_str.encode()).hexdigest()

    def is_valid_pow(self) -> bool:
        return self.hash.startswith(POW_DIFFICULTY)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        transactions = [Transaction.from_dict(tx) for tx in data["transactions"]]
        block = cls.__new__(cls)
        block.index = data["index"]
        block.previous_hash = data["previous_hash"]
        block.transactions = transactions
        block.nonce = data["nonce"]
        block.timestamp = data["timestamp"]
        block.hash = data["hash"]
        return block

    @classmethod
    def create_genesis(cls) -> "Block":
        genesis = cls.__new__(cls)
        genesis.index = 0
        genesis.previous_hash = "0" * 64
        genesis.transactions = []
        genesis.nonce = 0
        genesis.timestamp = 0.0
        genesis.hash = GENESIS_HASH
        return genesis

    def __repr__(self):
        return f"Block(index={self.index}, hash={self.hash[:16]}..., txs={len(self.transactions)})"
