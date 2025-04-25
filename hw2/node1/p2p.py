import socket
import threading
import os
import hashlib
import sys
import time
from collections import Counter
from blockchain import Blockchain

PEERS = [('172.17.0.2', 8001), ('172.17.0.3', 8002), ('172.17.0.4', 8003)]
TIMEOUT = 3

class P2PNode:
    def __init__(self, port, peers):
        self.port = port
        self.peers = peers
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.blockchain = Blockchain()
        self.blockchain.load_from_files()
        self.self_ip = '172.17.0.2'
        self.self_addr = (self.self_ip, self.port)

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()
        self._command_interface()

    def _listen(self):
        while True:
            data, addr = self.sock.recvfrom(8192)
            msg = data.decode('utf-8')

            if addr == self.self_addr:
                continue  # 忽略自己發送的訊息

            if msg == "CHECK_LAST_HASH":
                chain_data = ""
                files = sorted([f for f in os.listdir('.') if f.endswith('.txt') and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
                for fname in files:
                    with open(fname, 'r', encoding='utf-8') as f:
                        chain_data += f.read()
                full_chain_hash = hashlib.sha256(chain_data.encode('utf-8')).hexdigest()
                self.sock.sendto(full_chain_hash.encode('utf-8'), addr)

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
                check_all_chains(parts[1])
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

        tx_data = f"TRANSACTION_BROADCAST: {transaction}"
        for peer in self.peers:
            if peer != self.self_addr:
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
            print(f"帳本鏈受損，受損區塊編號:{result}")

    def _add_reward_and_broadcast(self, reward_tx):
        if not self.blockchain.blocks or len(self.blockchain.blocks[-1].transactions) >= 5:
            self.blockchain.add_block([reward_tx])
        else:
            self.blockchain.blocks[-1].transactions.append(reward_tx)

        self.blockchain.save_new_block_to_file(self.blockchain.blocks[-1])
        print(f"Reward transaction written: {reward_tx}")

        msg = f"REWARD_BROADCAST: {reward_tx}"
        for peer in self.peers:
            if peer != self.self_addr:
                self.sock.sendto(msg.encode('utf-8'), peer)

# --- checkAllChains 相關函數 ---
def send_check_last_hash(sock, peers):
    for peer in peers:
        sock.sendto("CHECK_LAST_HASH".encode('utf-8'), peer)

def request_all_chains(sock):
    for peer in PEERS:
        sock.sendto("REQUEST_CHAIN".encode('utf-8'), peer)

def listen_for_responses(sock, expected, results):
    received = 0
    while received < expected:
        try:
            sock.settimeout(TIMEOUT)
            data, addr = sock.recvfrom(1024)
            hash_value = data.decode('utf-8')
            results[addr] = hash_value
            print(f"Received from {addr}: {hash_value}")
            received += 1
        except socket.timeout:
            print("Timeout waiting for responses.")
            break

def receive_chains(sock, timeout=5):
    sock.settimeout(timeout)
    chains = {}
    try:
        while True:
            data, addr = sock.recvfrom(8192)
            text = data.decode('utf-8')
            if text.startswith("CHAIN:"):
                filename, content = text.split('\n', 1)
                if addr not in chains:
                    chains[addr] = {}
                chains[addr][filename.replace("CHAIN:", "").strip()] = content
    except socket.timeout:
        pass
    return chains

def hash_chain(chain_dict):
    all_data = ""
    for i in range(1, len(chain_dict) + 1):
        fname = f"{i}.txt"
        all_data += chain_dict.get(fname, "")
    return hashlib.sha256(all_data.encode('utf-8')).hexdigest()

def find_majority_chain(chains):
    hashes = [hash_chain(c) for c in chains.values()]
    counter = Counter(hashes)
    most_common, count = counter.most_common(1)[0]
    if count > len(chains) // 2:
        print(f"Majority chain found with {count} votes.")
        for addr, chain in chains.items():
            if hash_chain(chain) == most_common:
                return chain
    else:
        print("No consensus. Chain is untrusted.")
        return None

def overwrite_local_chain(chain_dict):
    for fname, content in chain_dict.items():
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)

def compare_hashes(results):
    peers = sorted(results.items(), key=lambda x: x[0][1])
    for i in range(len(peers)):
        for j in range(i + 1, len(peers)):
            addr1, hash1 = peers[i]
            addr2, hash2 = peers[j]
            verdict = "Yes" if hash1 == hash2 else "No"
            print(f"Compare {addr1} and {addr2}: {verdict}")

def validate_local_chain():
    blockchain = Blockchain()
    blockchain.load_from_files()
    for i in range(1, len(blockchain.blocks)):
        prev_hash = blockchain.blocks[i-1].hash
        if blockchain.blocks[i].previous_hash != prev_hash:
            print(f"Local chain corrupted at block {i+1}")
            return False
    return True

def broadcast_transaction(transaction):
    prefix = "REWARD_BROADCAST: "
    msg = prefix + transaction
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for peer in PEERS:
            sock.sendto(msg.encode('utf-8'), peer)
        time.sleep(0.02)

def reward_user(user):
    blockchain = Blockchain()
    blockchain.load_from_files()

    reward_tx = f"angel, {user}, 100"
    if not blockchain.blocks or len(blockchain.blocks[-1].transactions) >= 5:
        blockchain.add_block([reward_tx])
    else:
        blockchain.blocks[-1].transactions.append(reward_tx)

    blockchain.save_new_block_to_file(blockchain.blocks[-1])
    broadcast_transaction(reward_tx)
    print(f"Verification complete! {user} received 100 from angel as reward and broadcasted.")

def check_all_chains(checker):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 0))

    results = {}
    print("Sending CHECK_LAST_HASH to all peers...")
    send_check_last_hash(sock, PEERS)

    print("Waiting for responses...")
    listener_thread = threading.Thread(target=listen_for_responses, args=(sock, len(PEERS), results))
    listener_thread.start()
    listener_thread.join()

    print("\nComparing hashes:")
    compare_hashes(results)

    print("\nRequesting chains...")
    request_all_chains(sock)
    chains = receive_chains(sock)
    majority_chain = find_majority_chain(chains)

    if majority_chain:
        overwrite_local_chain(majority_chain)
        print("Local chain updated with majority chain.")
        print("\nValidating local blockchain...")
        if validate_local_chain():
            reward_user(checker)
        else:
            print("Local blockchain is invalid. No reward given.")
    else:
        print("Consensus failed. Chain is not trusted.")

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == "--checkAllChains":
        check_all_chains(sys.argv[2])
    else:
        port = 8001
        node = P2PNode(port, PEERS)
        node.start()
