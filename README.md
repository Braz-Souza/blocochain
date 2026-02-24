# blocochain - Implementação de uma Criptomoeda/Transação Distribuída Simplificada (Bitcoin-like)


**Equipe:**

BRAZ GABRIEL SILVA DE SOUZA - 202204940018

ITALO MARTINS COSTA - 201404940032

LUIZ EDUARDO MONTEIRO DOS SANTOS - 201904940032

**Disciplina:**

Laboratório de Sistemas Distribuídos - 2025.4

---

## Execução

para rodar basta utilizar no bootstrap

```bash
python3 run_node.py --host <seu_host> --port <sua_porta> 
```

nos outros que conectam ao bootstrap

```bash
python3 run_node.py --host <seu_host> --port <sua_porta> --bootstrap <host_bootstrap>:<porta_bootstrap>
```

## Estrutura

```bash
.
├── README.md
├── run_node.py
└── src
    ├── __init__.py
    ├── core
    │   ├── __init__.py
    │   ├── block.py
    │   ├── blockchain.py
    │   ├── miner.py
    │   └── transaction.py
    └── network
        ├── __init__.py
        ├── node.py
        └── protocol.py
```

## Sobre a Estrutura
run_node: roda o nó para conectar com o servidor

core/: diretorio que contem scripts essenciais para funcionamento do núcleo do nó

network/: diretorio contendo protocolos de rede e conexão entre nós

core/block.py: arquivo que define o bloco, no formato definido pela turma

core/blockchain.py: arquivo que define as funcoes da blockchain

core/mine.py: arquivo de mineracao da hash, com valor de retorno igual ao definido pela turma

core/transaction.py: define o objeto de transacao

network/node.py: organiza e executa funcoes de rede, como a sincronizacao automatica do nodo a cada 2 segundos

network/protocol.py: definicao de mensagens e protocolos de rede entre nos da blockchain

