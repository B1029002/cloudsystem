# B1029002 王琮翔 B1029043 楊景珺 B1029052 黃御嘉
from blockchain import Blockchain
import sys

if len(sys.argv) < 2:
    print("Please enter user name, ex. python app_checkMoney.py A")
    sys.exit(1)

target_user = sys.argv[1]

blockchain = Blockchain()
blockchain.load_from_files()

balance = 0

for block in blockchain.blocks:
    for tx in block.transactions:
        parts = tx.split(', ')
        if len(parts) == 3:
            sender, receiver, amount = parts[0], parts[1], int(parts[2])
            if receiver == target_user:
                balance += amount
            if sender == target_user and sender != "angel":
                balance -= amount

print(f"The amount of {target_user} is: {balance}")
