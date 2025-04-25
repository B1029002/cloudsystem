import hashlib
import os

class Block:
    def __init__(self, transactions, previous_hash, next_block=None):
        self.transactions = transactions
        self.previous_hash = previous_hash.strip()
        self.hash = None  # 初始為 None，等區塊寫入檔案後再用檔案內容計算
        self.next_block = next_block

    def calculate_hash_from_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return hashlib.sha256(content.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.head = None
        self.tail = None
        self.blocks = []

    def add_block(self, transactions):
        previous_hash = self.blocks[-1].hash if self.blocks else "None"
        block = Block(transactions, previous_hash)
        if self.blocks:
            self.blocks[-1].next_block = block
        self.blocks.append(block)
        self.save_new_block_to_file(block)

    def save_new_block_to_file(self, block):
        index = len(self.blocks)
        filename = f"{index}.txt"
        next_block_name = f"{index+1}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Sha256 of previous block: {block.previous_hash}\n")
            f.write(f"Next block: {next_block_name}\n")
            for tx in block.transactions:
                f.write(tx.strip() + "\n")
        block.hash = block.calculate_hash_from_file(filename)

    def load_from_files(self):
        i = 1
        self.blocks = []
        self.head = None
        prev_block = None

        while True:
            filename = f"{i}.txt"
            if not os.path.exists(filename):
                break

            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
                prev_hash_line = lines[0]
                prev_hash = prev_hash_line.replace("Sha256 of previous block: ", "").strip()
                transactions = [line.strip() for line in lines[2:]]

                block = Block(transactions, prev_hash)
                block.hash = block.calculate_hash_from_file(filename)

                if not self.blocks:
                    self.head = block
                else:
                    prev_block.next_block = block

                self.blocks.append(block)
                prev_block = block
                i += 1