import socket
import threading
import os
import sys
import time
import json
from blockchain import Blockchain

class P2PNode:
    def __init__(self, self_ip, port):
        self.self_ip = self_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.blockchain = Blockchain()
        self.blockchain.load_from_files()
        all_peers = [('172.17.0.2', 8001), ('172.17.0.3', 8001), ('172.17.0.4', 8001)]
        self.peers = [peer for peer in all_peers if peer[0] != self.self_ip]
        self.received_chains = {}

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()
        self._command_interface()

    def _listen(self):
        while True:
            data, addr = self.sock.recvfrom(65536)
            msg = data.decode('utf-8')

            if msg.startswith("CHECK_ALL_REQUEST:"):
                sender = msg.split(":")[1]
                print(f"Received checkAllChains request from {sender}")
                chain_data = self._gather_blockchain_contents()
                reply = {"type": "CHAIN_DATA", "ip": self.self_ip, "chain": chain_data}
                for peer in self.peers:
                    self.sock.sendto(json.dumps(reply).encode('utf-8'), peer)
                self.received_chains[self.self_ip] = chain_data

            elif msg.startswith("{\"type\": \"CHAIN_DATA\""):
                data = json.loads(msg)
                ip = data["ip"]
                chain = data["chain"]
                self.received_chains[ip] = chain

            elif msg.startswith("{\"type\": \"SYNC_BLOCK\""):
                data = json.loads(msg)
                index = data["index"]
                content = data["content"]
                self._sync_block(index, content)

            elif msg.startswith("TRANSACTION_BROADCAST: "):
                tx = msg.replace("TRANSACTION_BROADCAST: ", "").strip()
                print(f"Received broadcast transaction: {tx}")
                if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
                    self.blockchain.add_block([tx])
                else:
                    self.blockchain.blocks[-1].transactions.append(tx)
                self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])

            elif msg.startswith("REWARD_BROADCAST: "):
                reward_tx = msg.replace("REWARD_BROADCAST: ", "").strip()
                print(f"Received reward broadcast: {reward_tx}")
                if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
                    self.blockchain.add_block([reward_tx])
                else:
                    self.blockchain.blocks[-1].transactions.append(reward_tx)
                self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])

            else:
                print(f"Received unknown message: {msg}")

    def _send_full_chain(self, addr):
        files = sorted([f for f in os.listdir('.') if f.endswith('.txt') and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
        for fname in files:
            with open(fname, 'r', encoding='utf-8') as f:
                content = f.read()
                msg = f"CHAIN:{fname}\n{content}"
                self.sock.sendto(msg.encode('utf-8'), addr)

    def _command_interface(self):
        while True:
            cmd_line = input("Enter a command (checkMoney, checkLog, transaction, checkChain, checkAllChains): ").strip()
            parts = cmd_line.split()
            if not parts:
                continue
            cmd = parts[0]
            if cmd == "checkMoney" and len(parts) == 2:
                self._check_money(parts[1])
            elif cmd == "checkLog" and len(parts) == 2:
                self._check_log(parts[1])
            elif cmd == "transaction" and len(parts) == 4:
                sender = parts[1]
                receiver = parts[2]
                try:
                    amount = int(parts[3])
                    self._transaction(sender, receiver, amount)
                except ValueError:
                    print("Invalid amount. Please enter a number.")
            elif cmd == "checkChain" and len(parts) == 2:
                self._check_chain(parts[1])
            elif cmd == "checkAllChains" and len(parts) == 2:
                self._check_all_chains(parts[1])
            else:
                print("Unknown or malformed command.")

    def _check_money(self, user):
        balances = {}
        for block in self.blockchain.blocks:
            for tx in block.transactions:
                parts = tx.split(', ')
                if len(parts) == 3:
                    s, r, a = parts[0], parts[1], int(parts[2])
                    if s != "angel":
                        balances[s] = balances.get(s, 0) - a
                    balances[r] = balances.get(r, 0) + a
        print(f"{user}: {balances.get(user, 0)}")

    def _check_log(self, user):
        found = False
        for i, block in enumerate(self.blockchain.blocks):
            for tx in block.transactions:
                parts = tx.split(', ')
                if len(parts) == 3:
                    sender, receiver, amount = parts[0], parts[1], parts[2]
                    if sender == user or receiver == user:
                        print(f"[Block {i+1}.txt]: {sender} → {receiver} : {amount}")
                        found = True
        if not found:
            print(f"{user} No transaction!")

    def _transaction(self, sender, receiver, amount):
        balances = {}
        for block in self.blockchain.blocks:
            for tx in block.transactions:
                parts = tx.split(', ')
                if len(parts) == 3:
                    s, r, a = parts[0], parts[1], int(parts[2])
                    if s != "angel":
                        balances[s] = balances.get(s, 0) - a
                    balances[r] = balances.get(r, 0) + a

        if sender != "angel" and balances.get(sender, 0) < amount:
            print(f"Transaction failed: {sender}, Not enough amount: {balances.get(sender, 0)}")
            return

        transaction = f"{sender}, {receiver}, {amount}"
        if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
            self.blockchain.add_block([transaction])
            block_index = len(self.blockchain.blocks)
        else:
            self.blockchain.blocks[-1].transactions.append(transaction)
            block_index = len(self.blockchain.blocks)

        self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])
        print(f"Transaction success, written in {block_index}.txt")

        for peer in self.peers:
            tx_data = f"TRANSACTION_BROADCAST: {transaction}"
            self.sock.sendto(tx_data.encode('utf-8'), peer)

    def _check_chain(self, checker):
        def validate_blockchain(blockchain):
            for i in range(1, len(blockchain.blocks)):
                prev_block = blockchain.blocks[i - 1]
                current_block = blockchain.blocks[i]
                if current_block.previous_hash != prev_block.hash:
                    print(f"Mismatch at block {i+1}: expected {prev_block.hash}, got {current_block.previous_hash}")
                    return i + 1
            return 0

        result = validate_blockchain(self.blockchain)
        if result == 0:
            print("OK")
            angel_tx = f"angel, {checker}, 10"
            self._add_reward_and_broadcast(angel_tx)
        else:
            print(f"帳本鍊受損，不給予獎勵")

    def _add_reward_and_broadcast(self, reward_tx):
        if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
            self.blockchain.add_block([reward_tx])
        else:
            self.blockchain.blocks[-1].transactions.append(reward_tx)
        self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])
        print(f"Reward transaction written: {reward_tx}")
        for peer in self.peers:
            msg = f"REWARD_BROADCAST: {reward_tx}"
            self.sock.sendto(msg.encode('utf-8'), peer)

    def _gather_blockchain_contents(self):
        contents = []
        files = sorted([f for f in os.listdir('.') if f.endswith('.txt') and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
        for fname in files:
            with open(fname, 'r', encoding='utf-8') as f:
                contents.append(f.read())
        return contents

    def _compare_hashes(self):
        nodes = list(self.received_chains.keys())
        comparison_results = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if self.received_chains[nodes[i]] == self.received_chains[nodes[j]]:
                    comparison_results.append(f"{nodes[i]} vs {nodes[j]} : Yes")
                else:
                    comparison_results.append(f"{nodes[i]} vs {nodes[j]} : No")
        for result in comparison_results:
            print(result)

    def _consensus(self):
        all_chains = self.received_chains
        if len(all_chains) <= 1:
            return

        chain_lengths = [len(chain) for chain in all_chains.values()]
        max_len = max(chain_lengths)
        consensus_blocks = {}

        for idx in range(max_len):
            block_versions = {}
            for chain in all_chains.values():
                if idx < len(chain):
                    content = chain[idx]
                    block_versions[content] = block_versions.get(content, 0) + 1

            majority_block = None
            for content, count in block_versions.items():
                if count > len(all_chains) // 2:
                    majority_block = content
                    break

            if majority_block is not None:
                self._sync_block(idx, majority_block)
                sync_msg = {"type": "SYNC_BLOCK", "index": idx, "content": majority_block}
                for peer in self.peers:
                    self.sock.sendto(json.dumps(sync_msg).encode('utf-8'), peer)

    def _sync_block(self, index, content):
        filename = f"{index+1}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.blockchain.load_from_files()
        print(f"Block {index+1}同步完成。")

    def _check_all_chains(self, checker):
        print(f"Starting checkAllChains by {checker}...")

        msg = f"CHECK_ALL_REQUEST:{checker}"
        for peer in self.peers:
            self.sock.sendto(msg.encode('utf-8'), peer)

        self.received_chains[self.self_ip] = self._gather_blockchain_contents()

        print("Waiting for nodes to reply...")
        time.sleep(5)

        self._compare_hashes()
        self._consensus()

        angel_tx = f"angel, {checker}, 100"
        self._add_reward_and_broadcast(angel_tx)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 p2p.py <self_ip>")
        sys.exit(1)

    self_ip = sys.argv[1]
    port = 8001
    node = P2PNode(self_ip, port)
    node.start()
