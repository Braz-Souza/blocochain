import logging
import time
from typing import Callable, Optional

from .block import Block
from .blockchain import Blockchain
from .transaction import Transaction

logger = logging.getLogger(__name__)

COINBASE_REWARD = 50.0


class Miner:
    def __init__(self, blockchain: Blockchain, miner_address: str):
        self.blockchain = blockchain
        self.miner_address = miner_address
        self._mining = False

    def mine_block(self, on_progress: Optional[Callable[[int], None]] = None) -> Optional[Block]:
        self._mining = True

        coinbase = Transaction(
            origem="coinbase",
            destino=self.miner_address,
            valor=COINBASE_REWARD,
        )

        transactions = [coinbase] + list(self.blockchain.pending_transactions)

        last_block = self.blockchain.last_block
        index = last_block.index + 1
        previous_hash = last_block.hash
        timestamp = time.time()
        nonce = 0

        logger.info(
            "Iniciando mineração do bloco %d com %d transações",
            index,
            len(transactions),
        )

        while self._mining:
            candidate = Block(
                index=index,
                previous_hash=previous_hash,
                transactions=transactions,
                nonce=nonce,
                timestamp=timestamp,
            )
            if candidate.is_valid_pow():
                self._mining = False
                logger.info(
                    "Bloco %d minerado! nonce=%d hash=%s",
                    index,
                    nonce,
                    candidate.hash[:16],
                )
                return candidate

            nonce += 1
            if on_progress and nonce % 10000 == 0:
                on_progress(nonce)

        logger.info("Mineração interrompida no nonce=%d", nonce)
        return None

    def stop(self):
        self._mining = False
