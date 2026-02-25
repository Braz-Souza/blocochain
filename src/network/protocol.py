import json
import struct
from dataclasses import dataclass, field
from enum import Enum


class MessageType(str, Enum):
    NEW_TRANSACTION = "NEW_TRANSACTION"
    NEW_BLOCK = "NEW_BLOCK"
    REQUEST_CHAIN = "REQUEST_CHAIN"
    RESPONSE_CHAIN = "RESPONSE_CHAIN"
    PING = "PING"
    PONG = "PONG"
    DISCOVER_PEERS = "DISCOVER_PEERS"
    PEERS_LIST = "PEERS_LIST"


@dataclass
class Message:
    type: MessageType
    payload: dict
    sender: str = ""

    def to_bytes(self) -> bytes:
        body = json.dumps(
            {"type": self.type.value, "payload": self.payload, "sender": self.sender},
            sort_keys=True,
        ).encode("utf-8")
        header = struct.pack(">I", len(body))
        return header + body

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        obj = json.loads(data.decode("utf-8"))
        return cls(
            type=MessageType(obj["type"]),
            payload=obj.get("payload", {}),
            sender=obj.get("sender", ""),
        )

    def __repr__(self):
        return f"Message(type={self.type.value}, sender={self.sender})"


class Protocol:
    @staticmethod
    def new_transaction(tx_dict: dict, sender: str = "") -> Message:
        return Message(type=MessageType.NEW_TRANSACTION, payload={"transaction": tx_dict}, sender=sender)

    @staticmethod
    def new_block(block_dict: dict, sender: str = "") -> Message:
        return Message(type=MessageType.NEW_BLOCK, payload={"block": block_dict}, sender=sender)

    @staticmethod
    def request_chain(sender: str = "") -> Message:
        return Message(type=MessageType.REQUEST_CHAIN, payload={}, sender=sender)

    @staticmethod
    def response_chain(chain_dict: dict, sender: str = "") -> Message:
        return Message(type=MessageType.RESPONSE_CHAIN, payload={"blockchain": chain_dict}, sender=sender)

    @staticmethod
    def ping(sender: str = "") -> Message:
        return Message(type=MessageType.PING, payload={}, sender=sender)

    @staticmethod
    def pong(sender: str = "") -> Message:
        return Message(type=MessageType.PONG, payload={}, sender=sender)

    @staticmethod
    def discover_peers(sender: str = "") -> Message:
        return Message(type=MessageType.DISCOVER_PEERS, payload={}, sender=sender)

    @staticmethod
    def peers_list(peers: list, sender: str = "") -> Message:
        return Message(type=MessageType.PEERS_LIST, payload={"peers": peers}, sender=sender)
