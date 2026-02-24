import logging
import threading
from typing import List, Optional, Set

from .block import Block
from .transaction import Transaction

logger = logging.getLogger(__name__)


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = [Block.create_genesis()]
        self.pending_transactions: List[Transaction] = []
        self._confirmed_tx_ids: Set[str] = set()
        self._pending_tx_ids: Set[str] = set()
        self._lock = threading.Lock()

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def get_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.destino == address:
                    balance += tx.valor
                if tx.origem == address:
                    balance -= tx.valor
        for tx in self.pending_transactions:
            if tx.destino == address:
                balance += tx.valor
            if tx.origem == address:
                balance -= tx.valor
        return balance

    def add_transaction(self, tx: Transaction, trusted: bool = False) -> bool:
        with self._lock:
            if tx.id in self._confirmed_tx_ids or tx.id in self._pending_tx_ids:
                logger.debug("Transação duplicada rejeitada: %s", tx.id)
                return False

            if not trusted and tx.origem != "coinbase":
                available = self.get_balance(tx.origem)
                if available < tx.valor:
                    logger.warning(
                        "Saldo insuficiente para %s: disponível=%.2f, solicitado=%.2f",
                        tx.origem,
                        available,
                        tx.valor,
                    )
                    return False

            self.pending_transactions.append(tx)
            self._pending_tx_ids.add(tx.id)
            logger.debug("Transação adicionada ao mempool: %s", tx.id)
            return True

    def _get_confirmed_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.destino == address:
                    balance += tx.valor
                if tx.origem == address:
                    balance -= tx.valor
        return balance

    def add_block(self, block: Block) -> bool:
        with self._lock:
            if not self.is_valid_block(block):
                logger.warning("Bloco inválido rejeitado: index=%d", block.index)
                return False

            self.chain.append(block)

            for tx in block.transactions:
                self._confirmed_tx_ids.add(tx.id)
                self._pending_tx_ids.discard(tx.id)
                try:
                    self.pending_transactions.remove(tx)
                except ValueError:
                    pass

            logger.info("Bloco %d adicionado à chain", block.index)
            return True

    def is_valid_block(self, block: Block) -> bool:
        last = self.last_block

        if block.index != last.index + 1:
            logger.debug(
                "Índice inválido: esperado %d, recebido %d",
                last.index + 1,
                block.index,
            )
            return False

        if block.previous_hash != last.hash:
            logger.debug(
                "previous_hash inválido: esperado %s, recebido %s",
                last.hash,
                block.previous_hash,
            )
            return False

        if not block.is_valid_pow():
            logger.debug("PoW inválido: hash=%s", block.hash)
            return False

        recalculated = block.calculate_hash()
        if block.hash != recalculated:
            logger.debug(
                "Hash não bate: armazenado=%s, recalculado=%s",
                block.hash,
                recalculated,
            )
            return False

        return True

    def is_valid_chain(self, chain: List[Block]) -> bool:
        if not chain:
            return False

        from .block import GENESIS_HASH
        if chain[0].hash != GENESIS_HASH:
            logger.debug("Hash do gênesis não confere")
            return False

        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            if current.index != previous.index + 1:
                return False
            if current.previous_hash != previous.hash:
                return False
            if not current.is_valid_pow():
                return False
            if current.hash != current.calculate_hash():
                return False

        return True

    def replace_chain(self, new_chain: List[Block]) -> bool:
        with self._lock:
            if len(new_chain) <= len(self.chain):
                logger.debug(
                    "Chain recebida não é maior: recebida=%d, local=%d",
                    len(new_chain),
                    len(self.chain),
                )
                return False

            if not self.is_valid_chain(new_chain):
                logger.warning("Chain recebida é inválida, ignorando")
                return False

            self.chain = new_chain

            self._confirmed_tx_ids = set()
            for block in self.chain:
                for tx in block.transactions:
                    self._confirmed_tx_ids.add(tx.id)

            self.pending_transactions = [
                tx for tx in self.pending_transactions
                if tx.id not in self._confirmed_tx_ids
            ]
            self._pending_tx_ids = {tx.id for tx in self.pending_transactions}

            logger.info("Chain substituída, novo tamanho: %d", len(self.chain))
            return True

    def to_dict(self) -> dict:
        return {"chain": [block.to_dict() for block in self.chain]}

    @classmethod
    def from_dict(cls, data: dict) -> "Blockchain":
        bc = cls.__new__(cls)
        bc.chain = [Block.from_dict(b) for b in data["chain"]]
        bc.pending_transactions = []
        bc._confirmed_tx_ids = set()
        bc._pending_tx_ids = set()
        for block in bc.chain:
            for tx in block.transactions:
                bc._confirmed_tx_ids.add(tx.id)
        return bc
