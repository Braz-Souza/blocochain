#!/usr/bin/env python3
import argparse
import logging
import sys
import time

from src.core.transaction import Transaction
from src.network.node import Node

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_node")


def parse_args():
    parser = argparse.ArgumentParser(description="Nó da blockchain Bitcoin-like")
    parser.add_argument("--host", default="localhost", help="Endereço de escuta (padrão: localhost)")
    parser.add_argument("--port", type=int, default=5000, help="Porta de escuta (padrão: 5000)")
    parser.add_argument(
        "--bootstrap",
        nargs="*",
        default=[],
        metavar="HOST:PORT",
        help="Peers iniciais para conectar (ex: localhost:5001 localhost:5002)",
    )
    return parser.parse_args()


def print_menu(node: Node):
    print("\n" + "=" * 50)
    print(f"  Nó: {node.address}  |  Blocos: {len(node.blockchain.chain)}  |  Peers: {len(node.peers)}")
    print("=" * 50)
    print("  1. Criar transação")
    print("  2. Ver transações pendentes")
    print("  3. Minerar bloco")
    print("  4. Ver blockchain")
    print("  5. Ver saldo de endereço")
    print("  6. Ver peers conectados")
    print("  7. Conectar a peer")
    print("  0. Sair")
    print("=" * 50)


def menu_create_transaction(node: Node):
    print("\n--- Criar Transação ---")
    origem = input("  Origem: ").strip()
    destino = input("  Destino: ").strip()
    try:
        valor = float(input("  Valor: ").strip())
    except ValueError:
        print("  [ERRO] Valor inválido.")
        return

    try:
        tx = Transaction(origem=origem, destino=destino, valor=valor)
    except ValueError as e:
        print(f"  [ERRO] {e}")
        return

    added = node.blockchain.add_transaction(tx, trusted=False)
    if added:
        print(f"  [OK] Transação criada: {tx.id}")
        from src.network.protocol import Protocol
        node._broadcast(Protocol.new_transaction(tx.to_dict(), sender=node.address))
    else:
        print("  [ERRO] Transação rejeitada (saldo insuficiente ou duplicada).")


def menu_pending_transactions(node: Node):
    print("\n--- Transações Pendentes ---")
    pending = node.blockchain.pending_transactions
    if not pending:
        print("  (nenhuma)")
        return
    for tx in pending:
        print(f"  [{tx.id[:8]}] {tx.origem} -> {tx.destino}: {tx.valor}")


def menu_mine(node: Node):
    print("\n--- Minerando Bloco ---")
    print("  Pressione Ctrl+C para cancelar.\n")
    try:
        node.mine()
        chain = node.blockchain.chain
        last = chain[-1]
        print(f"  [OK] Bloco {last.index} minerado!")
        print(f"       Hash: {last.hash}")
        print(f"       Transações: {len(last.transactions)}")
    except KeyboardInterrupt:
        node.miner.stop()
        print("\n  [INFO] Mineração cancelada pelo usuário.")


def menu_view_blockchain(node: Node):
    print("\n--- Blockchain ---")
    for block in node.blockchain.chain:
        print(f"  Bloco {block.index}")
        print(f"    Hash:          {block.hash}")
        print(f"    Previous Hash: {block.previous_hash}")
        print(f"    Nonce:         {block.nonce}")
        print(f"    Transações:    {len(block.transactions)}")
        for tx in block.transactions:
            print(f"      [{tx.id[:8]}] {tx.origem} -> {tx.destino}: {tx.valor}")
        print()


def menu_balance(node: Node):
    print("\n--- Saldo ---")
    address = input("  Endereço: ").strip()
    balance = node.blockchain.get_balance(address)
    print(f"  Saldo de '{address}': {balance:.2f}")


def menu_peers(node: Node):
    print("\n--- Peers Conectados ---")
    if not node.peers:
        print("  (nenhum)")
        return
    for peer in sorted(node.peers):
        print(f"  {peer}")


def menu_connect_peer(node: Node):
    print("\n--- Conectar a Peer ---")
    peer = input("  Endereço (host:port): ").strip()
    if not peer:
        print("  [ERRO] Endereço vazio.")
        return
    node.connect_to_peer(peer)
    if peer in node.peers:
        print(f"  [OK] Conectado a {peer}")
    else:
        print(f"  [ERRO] Não foi possível conectar a {peer}")



def interactive_menu(node: Node):
    handlers = {
        "1": menu_create_transaction,
        "2": menu_pending_transactions,
        "3": menu_mine,
        "4": menu_view_blockchain,
        "5": menu_balance,
        "6": menu_peers,
        "7": menu_connect_peer,
    }

    while True:
        print_menu(node)
        try:
            choice = input("  Escolha: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Saindo...")
            sys.exit(0)

        if choice == "0":
            print("  Saindo...")
            sys.exit(0)

        handler = handlers.get(choice)
        if handler:
            handler(node)
        else:
            print("  [ERRO] Opção inválida.")


def main():
    args = parse_args()

    node = Node(host=args.host, port=args.port)

    def _on_peer_change(count: int):
        print(f"\n  [REDE] Peers conectados: {count}")
        print("  Escolha: ", end="", flush=True)

    def _on_block_change(total: int):
        print(f"\n  [BLOCO] Chain atualizada: {total} blocos")
        print("  Escolha: ", end="", flush=True)

    node.on_peer_change = _on_peer_change
    node.on_block_change = _on_block_change
    node.start()
    print(f"[OK] Nó iniciado em {node.address}")

    for peer in args.bootstrap:
        peer = peer.strip()
        if peer:
            print(f"[...] Conectando ao peer bootstrap: {peer}")
            node.connect_to_peer(peer)

    if args.bootstrap:
        print("[...] Sincronizando blockchain...")
        node.sync_blockchain()
        print(f"[OK] Blockchain sincronizada: {len(node.blockchain.chain)} blocos")

    interactive_menu(node)


if __name__ == "__main__":
    main()
