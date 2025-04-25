import random
import socket
import time

# 所有節點的 IP 和 PORT 設定
PEERS = [('127.0.0.1', 8001), ('127.0.0.1', 8002), ('127.0.0.1', 8003)]
LOCAL_PORT = 8001  # ⚠️ 改為你執行此程式的 port

balances = {
    "A": 0,
    "B": 0,
    "C": 0
}

# 廣播交易到所有節點（包含自己）
def broadcast_transaction(transaction, is_reward=False):
    prefix = "REWARD_BROADCAST: " if is_reward else "TRANSACTION_BROADCAST: "
    msg = prefix + transaction
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for peer in PEERS:
            sock.sendto(msg.encode('utf-8'), peer)
        time.sleep(0.02)  # 延遲避免封包掉落

# 隨機產生一筆交易
def generate_transaction():
    all_possible_senders = list(balances.keys()) + ["angel"]
    sender = random.choice(all_possible_senders)
    receivers = [user for user in balances if user != sender]
    receiver = random.choice(receivers)

    if sender == "angel":
        amount = random.randint(1, 100)
    else:
        if balances[sender] == 0:
            return None
        amount = random.randint(1, balances[sender])

    if sender != "angel":
        balances[sender] -= amount
    balances[receiver] += amount

    return f"{sender}, {receiver}, {amount}"

def main():
    all_transactions = []
    while len(all_transactions) < 100:
        tx = generate_transaction()
        if tx:
            all_transactions.append(tx)
            is_reward = tx.startswith("angel")
            broadcast_transaction(tx, is_reward=is_reward)
            print(f"📤 Broadcasted: {tx}")
            time.sleep(0.05)

    print("\n✅ 所有 100 筆交易已廣播完成。")

if __name__ == "__main__":
    main()