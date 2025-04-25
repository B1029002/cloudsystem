import socket
import sys
import time
import threading
import hashlib
from collections import Counter
from blockchain import Blockchain

PEERS = [('127.0.0.1', 8001), ('127.0.0.1', 8002), ('127.0.0.1', 8003)]
TIMEOUT = 3


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

def receive_chains(sock, timeout=5):
    sock.settimeout(timeout)
    chains = {}
    try:
        while True:
            data, addr = sock.recvfrom(8192)
            text = data.decode('utf-8')
            if text.startswith("CHAIN:"):
                filename, content = text.split('\n', 1)
                if addr not in chains:
                    chains[addr] = {}
                chains[addr][filename.replace("CHAIN:", "").strip()] = content
    except socket.timeout:
        pass
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
    peers = sorted(results.items(), key=lambda x: x[0][1])
    for i in range(len(peers)):
        for j in range(i + 1, len(peers)):
            addr1, hash1 = peers[i]
            addr2, hash2 = peers[j]
            verdict = "Yes" if hash1 == hash2 else "No"
            print(f"Compare {addr1} and {addr2}: {verdict}")

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

def main():
    if len(sys.argv) != 2:
        print("Usage: python checkAllChains.py [username]")
        return

    checker = sys.argv[1]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 0))

    results = {}
    print("Sending CHECK_LAST_HASH to all peers...")
    send_check_last_hash(sock, PEERS)

    print("Waiting for responses...")
    listener_thread = threading.Thread(target=listen_for_responses, args=(sock, len(PEERS), results))
    listener_thread.start()
    listener_thread.join()

    print("\nComparing hashes:")
    compare_hashes(results)

    print("\nRequesting chains...")
    request_all_chains(sock)
    chains = receive_chains(sock)
    majority_chain = find_majority_chain(chains)

    if majority_chain:
        overwrite_local_chain(majority_chain)
        print("Local chain updated with majority chain.")
        print("\nValidating local blockchain...")
        if validate_local_chain():
            reward_user(checker)
        else:
            print("Local blockchain is invalid. No reward given.")
    else:
        print("Consensus failed. Chain is not trusted.")

if __name__ == "__main__":
    main()