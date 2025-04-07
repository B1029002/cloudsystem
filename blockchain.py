# B1029002 王琮翔 B1029043 楊景珺 B1029052 黃御嘉
import hashlib
import os

class Block:
    def __init__(self, transactions, previous_hash, next_block=None):
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()
        self.next_block = next_block

    def calculate_hash(self):
        data = "".join(self.transactions) + self.previous_hash
        return hashlib.sha256(data.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.head = None
        self.tail = None
        self.blocks = []

    def add_block(self, transactions):
        previous_hash = self.blocks[-1].hash if self.blocks else "..."
        block = Block(transactions, previous_hash)
        if self.blocks:
            self.blocks[-1].next_block = block
        self.blocks.append(block)

    def save_to_files(self):
        for i, block in enumerate(self.blocks):
            filename = f"{i+1}.txt"
            next_block_name = f"{i+2}.txt" if i+1 < len(self.blocks) else "None"
            with open(filename, 'w') as f:
                f.write(f"Sha256 of previous block: {block.previous_hash}\n")
                f.write(f"Next block: {next_block_name}\n")
                for tx in block.transactions:
                    f.write(tx + "\n")

    def load_from_files(self):
        i = 1
        self.blocks = []
        self.head = None
        prev_block = None

        while True:
            filename = f"{i}.txt"
            if not os.path.exists(filename):
                break

            with open(filename, 'r') as f:
                lines = f.read().splitlines()
                prev_hash_line = lines[0]
                prev_hash = prev_hash_line.replace("Sha256 of previous block: ", "")

                transactions = lines[2:] 

                block = Block(transactions, prev_hash)

                if not self.blocks:
                    self.head = block
                else:
                    prev_block.next_block = block

                self.blocks.append(block)
                prev_block = block
                i += 1
