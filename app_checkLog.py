from blockchain import Blockchain
import sys

if len(sys.argv) < 2:
    print("Please enter user name, ex. python app_checkLog.py A")
    sys.exit(1)

target_user = sys.argv[1]

blockchain = Blockchain()
blockchain.load_from_files()

found = False

for i, block in enumerate(blockchain.blocks):
    for tx in block.transactions:
        parts = tx.split(', ')
        if len(parts) == 3:
            sender, receiver, amount = parts
            if sender == target_user or receiver == target_user:
                print(f"[{i+1}.txt]: {sender}, {receiver}, {amount}")
                found = True

if not found:
    print(f"{target_user} No transaction!")
