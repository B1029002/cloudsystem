import socket
import threading
import os
import sys
import time
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
        self.received_hashes = {}

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()
        self._command_interface()

    def _listen(self):
        while True:
            data, addr = self.sock.recvfrom(8192)
            msg = data.decode('utf-8')

            if msg == "CHECK_LAST_HASH":
                last_hash = self.blockchain.blocks[-1].hash
                self.sock.sendto(last_hash.encode('utf-8'), addr)

            elif msg == "REQUEST_CHAIN":
                self._send_full_chain(addr)

            elif msg.startswith("TRANSACTION_BROADCAST: "):
                tx = msg.replace("TRANSACTION_BROADCAST: ", "").strip()
                print(f"Received broadcast transaction: {tx} from {addr}")
                if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
                    self.blockchain.add_block([tx])
                else:
                    self.blockchain.blocks[-1].transactions.append(tx)
                self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])
                print("Transaction written to local blockchain.")

            elif msg.startswith("REWARD_BROADCAST: "):
                reward_tx = msg.replace("REWARD_BROADCAST: ", "").strip()
                print(f"Received reward broadcast: {reward_tx} from {addr}")
                if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
                    self.blockchain.add_block([reward_tx])
                else:
                    self.blockchain.blocks[-1].transactions.append(reward_tx)
                self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])
                print("Reward written to local blockchain.")

            elif msg.startswith("CHECK_ALL_REQUEST:"):
                sender = msg.split(":")[1]
                print(f"Received checkAllChains request from {sender}")
                my_hash = self._calculate_full_chain_hash()
                reply = f"CHECK_ALL_RESULT:{self.self_ip}:{my_hash}"
                for peer in self.peers:
                    self.sock.sendto(reply.encode('utf-8'), peer)
                self.received_hashes[self.self_ip] = my_hash

            elif msg.startswith("CHECK_ALL_RESULT:"):
                parts = msg.split(":")
                node_ip = parts[1]
                hash_value = parts[2]
                self.received_hashes[node_ip] = hash_value

            elif msg.startswith("CHAIN:"):
                pass

            else:
                print(f"Received unknown message: {msg} from {addr}")

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
            print(f"帳本鍊受損，受損區塊編號:{result}，不給予獎勵")

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

    def _calculate_full_chain_hash(self):
        full_content = ""
        files = sorted([f for f in os.listdir('.') if f.endswith('.txt') and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
        for fname in files:
            with open(fname, 'r', encoding='utf-8') as f:
                full_content += f.read()
        return self.blockchain.calculate_hash(full_content)

    def _compare_hashes(self):
        nodes = list(self.received_hashes.keys())
        comparison_results = []
        all_match = True

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1, n2 = nodes[i], nodes[j]
                if self.received_hashes[n1] == self.received_hashes[n2]:
                    comparison_results.append(f"{n1} vs {n2} : Yes")
                else:
                    comparison_results.append(f"{n1} vs {n2} : No")
                    all_match = False

        for result in comparison_results:
            print(result)

        if not all_match:
            wrong_block = self._find_wrong_block()
            if wrong_block != -1:
                print(f"有誤在 {wrong_block}.txt")
            else:
                print("有誤但找不到是哪個區塊")

    def _find_wrong_block(self):
        for i in range(1, len(self.blockchain.blocks)):
            prev_block = self.blockchain.blocks[i - 1]
            current_block = self.blockchain.blocks[i]
            if current_block.previous_hash != prev_block.hash:
                return i + 1
        return -1

    def _check_all_chains(self, checker):
        print(f"Starting checkAllChains by {checker}...")

        self_check_result = self._validate_full_blockchain()
        if self_check_result != 0:
            print(f"Local chain error at block {self_check_result}. Aborting.")
            return

        msg = f"CHECK_ALL_REQUEST:{checker}"
        for peer in self.peers:
            self.sock.sendto(msg.encode('utf-8'), peer)

        my_hash = self._calculate_full_chain_hash()
        self.received_hashes[self.self_ip] = my_hash

        print("Waiting for nodes to reply...")
        time.sleep(5)

        self._compare_hashes()

        angel_tx = f"angel, {checker}, 100"
        self._add_reward_and_broadcast(angel_tx)

    def _validate_full_blockchain(self):
        for i in range(1, len(self.blockchain.blocks)):
            prev_block = self.blockchain.blocks[i - 1]
            current_block = self.blockchain.blocks[i]
            if current_block.previous_hash != prev_block.hash:
                return i + 1
        return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 p2p.py <self_ip>")
        sys.exit(1)

    self_ip = sys.argv[1]
    port = 8001
    node = P2PNode(self_ip, port)
    node.start()
