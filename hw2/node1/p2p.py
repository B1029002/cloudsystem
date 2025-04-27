import socket
import threading
import os
from blockchain import Blockchain

class P2PNode:
    def __init__(self, port, peers):
        self.port = port
        self.peers = peers
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.blockchain = Blockchain()
        self.blockchain.load_from_files()

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
            cmd_line = input("Enter a command (checkMoney, checkLog, transaction, checkChain): ").strip()
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
        print("OK" if result == 0 else f"帳本鍊受損，受損區塊編號:{result}")

        angel_tx = f"angel, {checker}, 10"
        self._add_reward_and_broadcast(angel_tx)

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

if __name__ == '__main__':
    import os

    my_ip = os.getenv("MY_IP")
    if my_ip == "172.17.0.2":
        port = 8001
        peers = [("172.17.0.3", 8001), ("172.17.0.4", 8001)]
    elif my_ip == "172.17.0.3":
        port = 8001
        peers = [("172.17.0.2", 8001), ("172.17.0.4", 8001)]
    elif my_ip == "172.17.0.4":
        port = 8001
        peers = [("172.17.0.2", 8001), ("172.17.0.3", 8001)]
    else:
        raise ValueError("Unknown IP, please set MY_IP environment variable correctly.")

    node = P2PNode(port, peers)
    node.start()
