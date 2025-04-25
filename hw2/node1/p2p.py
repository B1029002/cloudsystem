import socket
import threading
import os
import hashlib
import sys
import time
from collections import Counter
from blockchain import Blockchain

PEERS = [('172.17.0.2', 8001), ('172.17.0.3', 8001), ('172.17.0.4', 8001)]
TIMEOUT = 3

def broadcast_chain(chain_dict):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for peer in PEERS:
            for fname, content in chain_dict.items():
                msg = f"CHAIN:{fname}\n{content}"
                sock.sendto(msg.encode('utf-8'), peer)
                time.sleep(0.01)

class P2PNode:
    def __init__(self, port, peers):
        self.port = port
        self.peers = peers
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.blockchain = Blockchain()
        self.blockchain.load_from_files()
        self.self_ip = socket.gethostbyname(socket.gethostname())
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
                self.blockchain.load_from_files()
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
                try:
                    header, content = msg.split('\n', 1)
                    filename = header.replace("CHAIN:", "").strip()
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"📥 Received and updated block: {filename}")
                except Exception as e:
                    print(f"❌ Error processing CHAIN message: {e}")

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
            # ✅ 僅在區塊鏈完全正確時才獎勵
            self._add_reward_and_broadcast(angel_tx)
        else:
            # ❌ 鏈損壞時不能進行任何交易或獎勵！
            print(f"帳本鏈受損，受損區塊編號:{result}")
            return

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

def receive_chains(sock, peers, timeout=3):
    chains = {}

    for peer in peers:
        print(f"\n📡 正在從 {peer} 接收鏈資料...")
        sock.sendto("REQUEST_CHAIN".encode('utf-8'), peer)

        sock.settimeout(timeout)
        peer_chain = {}
        try:
            while True:
                data, addr = sock.recvfrom(8192)
                if addr != peer:
                    continue  # 只接收來自該 peer 的資料

                text = data.decode('utf-8')
                if text.startswith("CHAIN:"):
                    filename, content = text.split('\n', 1)
                    filename = filename.replace("CHAIN:", "").strip()
                    peer_chain[filename] = content
        except socket.timeout:
            print(f"✅ 從 {peer} 接收完成，共收到 {len(peer_chain)} 個區塊檔案。")

        chains[peer] = peer_chain

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
    sorted_peers = sorted(results.items(), key=lambda x: x[0][1])  # 根據 port 排序
    labels = {}
    for idx, (addr, _) in enumerate(sorted_peers):
        labels[addr] = f"client{idx + 1}"

    print("[比對中] 與其他 client 帳本進行對比：")
    for i in range(len(sorted_peers)):
        for j in range(i + 1, len(sorted_peers)):
            addr1, hash1 = sorted_peers[i]
            addr2, hash2 = sorted_peers[j]
            verdict = "✅" if hash1 == hash2 else "❌"
            print(f"{labels[addr1]} vs {labels[addr2]}: {verdict}")


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

    chains = receive_chains(sock, PEERS)

    # ✅ 加入自己本地的鏈
    local_chain = {}
    files = sorted([f for f in os.listdir('.') if f.endswith('.txt') and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
    for fname in files:
        with open(fname, 'r', encoding='utf-8') as f:
            local_chain[fname] = f.read()

    local_ip = socket.gethostbyname(socket.gethostname())
    local_addr = (local_ip.strip(), 8001)
    chains[local_addr] = local_chain

    addr_to_hash = {}
    for addr, chain_dict in chains.items():
        clean_addr = (addr[0].strip(), addr[1])
        addr_to_hash[clean_addr] = hash_chain(chain_dict)

    print("\n[各節點雜湊值]")
    for addr, h in addr_to_hash.items():
        print(f"{addr[0]}:{addr[1]} → {h}")

    print("\n[比對結果]")
    addrs = list(addr_to_hash.keys())
    for i in range(len(addrs)):
        for j in range(i + 1, len(addrs)):
            addr1, addr2 = addrs[i], addrs[j]
            h1, h2 = addr_to_hash[addr1], addr_to_hash[addr2]
            verdict = "✅" if h1 == h2 else "❌"
            print(f"{addr1[1]} vs {addr2[1]}: {verdict}")

    print("\n[診斷] 檢查每個節點是否與多數一致：")
    hash_counts = Counter(addr_to_hash.values())
    most_common_hash, _ = hash_counts.most_common(1)[0]
    for addr, h in addr_to_hash.items():
        if h == most_common_hash:
            print(f"{addr[0]}:{addr[1]} ✔️ 一致")
        else:
            print(f"{addr[0]}:{addr[1]} ⚠️ 與多數不一致（可能被竄改）")

    print("\n嘗試同步鏈內容...")
    majority_chain = None
    for addr, chain_dict in chains.items():
        if hash_chain(chain_dict) == most_common_hash:
            majority_chain = chain_dict
            break

    if majority_chain:
        overwrite_local_chain(majority_chain)
        broadcast_chain(majority_chain)
        print("📥 Local chain updated and broadcasted to others.")

        print("✅ Validating updated local blockchain...")
        if validate_local_chain():
            reward_user(checker)
        else:
            print("❌ Updated local blockchain is invalid. No reward given.")
    else:
        print("❌ Consensus failed. Chain is not trusted.")





if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == "--checkAllChains":
        check_all_chains(sys.argv[2])
    else:
        port = 8001
        node = P2PNode(port, PEERS)
        node.start()
