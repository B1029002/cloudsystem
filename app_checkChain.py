from blockchain import Blockchain
import sys

if len(sys.argv) < 2:
    print("Please enter user name, ex. python app_checkChain.py A")
    sys.exit(1)

checker = sys.argv[1]

def validate_blockchain(blockchain):
    for i in range(1, len(blockchain.blocks)):
        prev_block = blockchain.blocks[i - 1]
        current_block = blockchain.blocks[i]
        if current_block.previous_hash != prev_block.calculate_hash():
            return i + 1  
    return 0 

def reward_checker(blockchain, user):
    reward_tx = f"angel, {user}, 10"
    if not blockchain.blocks or len(blockchain.blocks[-1].transactions) >= 5:
        blockchain.add_block([reward_tx])
    else:
        blockchain.blocks[-1].transactions.append(reward_tx)
    blockchain.save_to_files()

def main():
    blockchain = Blockchain()
    blockchain.load_from_files()

    result = validate_blockchain(blockchain)
    
    if result == 0:
        print("OK")
        print(f"{checker} get 10 dollars from angel")
    else:
        print(f"帳本鍊受損，受損區塊編號: {result}")

    reward_checker(blockchain, checker)

if __name__ == "__main__":
    main()
