import logging
import socket
import struct
import threading
from typing import Callable, Optional, Set

from ..core.block import Block
from ..core.blockchain import Blockchain
from ..core.miner import Miner
from ..core.transaction import Transaction
from .protocol import Message, MessageType, Protocol

logger = logging.getLogger(__name__)

SOCKET_TIMEOUT = 5.0
RECV_BUFFER = 4096
SYNC_INTERVAL = 2.0


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Conexão encerrada antes de receber todos os bytes")
        data += chunk
    return data


class Node:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"

        self.blockchain = Blockchain()
        self.miner = Miner(self.blockchain, self.address)

        self.peers: Set[str] = set()
        self._mining_thread: Optional[threading.Thread] = None
        self._server_sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self.on_peer_change: Optional[Callable[[int], None]] = None
        self.on_block_change: Optional[Callable[[int], None]] = None

    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(10)
        logger.info("Nó iniciado em %s", self.address)

        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def _add_peer(self, peer: str):
        """Adiciona peer ao set e dispara callback se for novo."""
        if peer and peer != self.address and peer not in self.peers:
            self.peers.add(peer)
            if self.on_peer_change:
                self.on_peer_change(len(self.peers))

    def _sync_loop(self):
        import time
        while True:
            time.sleep(SYNC_INTERVAL)
            with self._lock:
                has_peers = bool(self.peers)
            if has_peers:
                logger.debug("Sync automático iniciado")
                self.sync_blockchain()

    def _accept_loop(self):
        while True:
            try:
                conn, addr = self._server_sock.accept()
                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
            except Exception as e:
                logger.debug("Erro no accept: %s", e)
                break

    def _handle_client(self, sock: socket.socket):
        try:
            sock.settimeout(SOCKET_TIMEOUT)
            header = _recv_exact(sock, 4)
            msg_len = struct.unpack(">I", header)[0]
            body = _recv_exact(sock, msg_len)
            msg = Message.from_bytes(body)

            response = self._dispatch(msg)
            if response:
                sock.sendall(response.to_bytes())
        except Exception as e:
            logger.debug("Erro ao tratar cliente: %s", e)
        finally:
            sock.close()

    def _dispatch(self, msg: Message) -> Optional[Message]:
        if msg.sender and msg.sender != self.address:
            with self._lock:
                self._add_peer(msg.sender)

        if msg.type == MessageType.PING:
            return self._on_ping(msg)
        elif msg.type == MessageType.PONG:
            return None
        elif msg.type == MessageType.NEW_TRANSACTION:
            return self._on_new_transaction(msg)
        elif msg.type == MessageType.NEW_BLOCK:
            return self._on_new_block(msg)
        elif msg.type == MessageType.REQUEST_CHAIN:
            return self._on_request_chain(msg)
        elif msg.type == MessageType.RESPONSE_CHAIN:
            return self._on_response_chain(msg)
        elif msg.type == MessageType.DISCOVER_PEERS:
            return self._on_discover_peers(msg)
        elif msg.type == MessageType.PEERS_LIST:
            return self._on_peers_list(msg)
        else:
            logger.warning("Tipo de mensagem desconhecido: %s", msg.type)
            return None

    def _on_ping(self, msg: Message) -> Message:
        return Protocol.pong(sender=self.address)

    def _on_new_transaction(self, msg: Message) -> None:
        try:
            tx = Transaction.from_dict(msg.payload["transaction"])
            added = self.blockchain.add_transaction(tx, trusted=False)
            if added:
                logger.info("Nova transação recebida: %s", tx.id[:8])
                self._broadcast(
                    Protocol.new_transaction(tx.to_dict(), sender=self.address),
                    exclude={msg.sender},
                )
        except Exception as e:
            logger.warning("Erro ao processar transação recebida: %s", e)
        return None

    def _on_new_block(self, msg: Message) -> None:
        try:
            block = Block.from_dict(msg.payload["block"])
            self.miner.stop()
            added = self.blockchain.add_block(block)
            if added:
                logger.info("Novo bloco recebido e adicionado: index=%d", block.index)
                if self.on_block_change:
                    self.on_block_change(len(self.blockchain.chain))
                self._broadcast(
                    Protocol.new_block(block.to_dict(), sender=self.address),
                    exclude={msg.sender},
                )
        except Exception as e:
            logger.warning("Erro ao processar bloco recebido: %s", e)
        return None

    def _on_request_chain(self, msg: Message) -> Message:
        if msg.sender and msg.sender != self.address:
            with self._lock:
                self._add_peer(msg.sender)
        return Protocol.response_chain(self.blockchain.to_dict(), sender=self.address)

    def _on_response_chain(self, msg: Message) -> None:
        try:
            bc = Blockchain.from_dict(msg.payload["blockchain"])
            replaced = self.blockchain.replace_chain(bc.chain)
            if replaced:
                logger.info("Chain local substituída pela recebida de %s", msg.sender)
        except Exception as e:
            logger.warning("Erro ao processar chain recebida: %s", e)
        return None

    def _on_discover_peers(self, msg: Message) -> Message:
        with self._lock:
            peers = list(self.peers - {msg.sender})
        return Protocol.peers_list(peers, sender=self.address)

    def _on_peers_list(self, msg: Message) -> None:
        peers = msg.payload.get("peers", [])
        for peer in peers:
            if peer != self.address:
                with self._lock:
                    known = peer in self.peers
                if not known:
                    self.connect_to_peer(peer)
        return None

    def _send_message(
        self, peer: str, msg: Message, expect_response: bool = False
    ) -> Optional[Message]:
        host, port_str = peer.rsplit(":", 1)
        port = int(port_str)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(SOCKET_TIMEOUT)
                sock.connect((host, port))
                sock.sendall(msg.to_bytes())
                if expect_response:
                    try:
                        header = _recv_exact(sock, 4)
                        msg_len = struct.unpack(">I", header)[0]
                        body = _recv_exact(sock, msg_len)
                        return Message.from_bytes(body)
                    except Exception:
                        return None
                return None
        except Exception as e:
            logger.debug("Falha ao enviar para %s: %s", peer, e)
            return None

    def _broadcast(self, msg: Message, exclude: set = None):
        exclude = exclude or set()
        with self._lock:
            targets = list(self.peers - exclude)

        def send(peer):
            self._send_message(peer, msg, expect_response=False)

        threads = [threading.Thread(target=send, args=(p,), daemon=True) for p in targets]
        for t in threads:
            t.start()

    def connect_to_peer(self, peer: str):
        if peer == self.address:
            return

        host, port_str = peer.rsplit(":", 1)
        port = int(port_str)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(SOCKET_TIMEOUT)
                sock.connect((host, port))

                msg = Protocol.request_chain(sender=self.address)
                sock.sendall(msg.to_bytes())

                response = None
                try:
                    header = _recv_exact(sock, 4)
                    msg_len = struct.unpack(">I", header)[0]
                    body = _recv_exact(sock, msg_len)
                    response = Message.from_bytes(body)
                except Exception:
                    pass

        except Exception as e:
            logger.warning("Não foi possível conectar ao peer: %s", peer)
            return

        with self._lock:
            self._add_peer(peer)
        logger.info("Peer conectado: %s", peer)

        if response and response.type == MessageType.RESPONSE_CHAIN:
            self._on_response_chain(response)

        # Descoberta de peers
        resp2 = self._send_message(
            peer, Protocol.discover_peers(sender=self.address), expect_response=True
        )
        if resp2 and resp2.type == MessageType.PEERS_LIST:
            self._on_peers_list(resp2)

    def sync_blockchain(self):
        with self._lock:
            targets = list(self.peers)

        if not targets:
            logger.info("Nenhum peer para sincronizar")
            return

        best_chain = self.blockchain.chain
        best_peer = None
        for peer in targets:
            response = self._send_message(
                peer, Protocol.request_chain(sender=self.address), expect_response=True
            )
            if response and response.type == MessageType.RESPONSE_CHAIN:
                try:
                    bc = Blockchain.from_dict(response.payload["blockchain"])
                    if (
                        len(bc.chain) > len(best_chain)
                        and self.blockchain.is_valid_chain(bc.chain)
                    ):
                        best_chain = bc.chain
                        best_peer = peer
                except Exception as e:
                    logger.debug("Erro ao processar chain de %s: %s", peer, e)

        if best_chain is not self.blockchain.chain:
            if self.blockchain.replace_chain(best_chain):
                top = self.blockchain.last_block
                logger.info("Sync: chain atualizada via sync, novo topo: index=%d", top.index)
                if self.on_block_change:
                    self.on_block_change(len(self.blockchain.chain))
                self._broadcast(
                    Protocol.new_block(top.to_dict(), sender=self.address),
                    exclude={best_peer} if best_peer else set(),
                )

    def mine(self):
        def _mine():
            def progress(nonce):
                print(f"\r  Minerando... nonce={nonce}", end="", flush=True)

            block = self.miner.mine_block(on_progress=progress)
            print()
            if block:
                added = self.blockchain.add_block(block)
                if added:
                    logger.info("Bloco minerado e adicionado localmente: index=%d", block.index)
                    self._broadcast(
                        Protocol.new_block(block.to_dict(), sender=self.address)
                    )
                    return block
            return None

        self._mining_thread = threading.Thread(target=_mine, daemon=True)
        self._mining_thread.start()
        self._mining_thread.join()
        return None
