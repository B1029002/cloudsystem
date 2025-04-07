# B1029002 王琮翔 B1029043 楊景珺 B1029052 黃御嘉
from blockchain import Blockchain
import sys

sender = sys.argv[1]
receiver = sys.argv[2]
amount = int(sys.argv[3])

if len(sys.argv) != 4:
    print("Please enter the right format, ex. python app_transaction.py A B 10")
    sys.exit(1)

blockchain = Blockchain()
blockchain.load_from_files()

balances = {}
for block in blockchain.blocks:
    for tx in block.transactions:
        parts = tx.split(', ')
        if len(parts) == 3:
            s, r, a = parts[0], parts[1], int(parts[2])
            if s != "angel":
                balances[s] = balances.get(s, 0) - a
            balances[r] = balances.get(r, 0) + a

if sender != "angel":
    if balances.get(sender, 0) < amount:
        print(f" Transaction failed: {sender} has insufficient funds. Balance: {balances.get(sender, 0)}")
        sys.exit(1)

transaction = f"{sender}, {receiver}, {amount}"

if not blockchain.blocks or len(blockchain.blocks[-1].transactions) >= 5:
    blockchain.add_block([transaction])
    block_index = len(blockchain.blocks)
else:
    blockchain.blocks[-1].transactions.append(transaction)
    block_index = len(blockchain.blocks)

blockchain.save_to_files()
print(f"Transaction success, written in {block_index}.txt")
