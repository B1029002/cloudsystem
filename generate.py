# B1029002 王琮翔 B1029043 楊景珺 B1029052 黃御嘉
import random
from blockchain import Blockchain

balances = {
    "A": 0,
    "B": 0,
    "C": 0
}

def generate_transaction():
    all_possible_senders = list(balances.keys()) + ["angel"]
    
    sender = random.choice(all_possible_senders)

    all_users = list(balances.keys())
    possible_receivers = [user for user in all_users if user != sender]
    receiver = random.choice(possible_receivers)

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
    blockchain = Blockchain()
    all_transactions = []

    while len(all_transactions) < 100:
        tx = generate_transaction()
        if tx:
            all_transactions.append(tx)

    for i in range(0, 100, 5):
        blockchain.add_block(all_transactions[i:i+5])

    blockchain.save_to_files()
    print("success")

if __name__ == "__main__":
    main()
