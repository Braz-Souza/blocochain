import uuid
import time
from dataclasses import dataclass, field


@dataclass
class Transaction:
    origem: str
    destino: str
    valor: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.origem:
            raise ValueError("origem não pode ser vazio")
        if not self.destino:
            raise ValueError("destino não pode ser vazio")
        if self.valor <= 0:
            raise ValueError(f"valor deve ser > 0, recebido: {self.valor}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "origem": self.origem,
            "destino": self.destino,
            "valor": self.valor,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        tx = cls.__new__(cls)
        tx.id = data["id"]
        tx.origem = data["origem"]
        tx.destino = data["destino"]
        tx.valor = data["valor"]
        tx.timestamp = data["timestamp"]
        return tx

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return False
        return self.id == other.id

    def __repr__(self):
        return f"Transaction(id={self.id[:8]}..., {self.origem} -> {self.destino}, {self.valor})"
