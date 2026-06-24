import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bitcoin import *
from colorama import Fore, Style, init
from tqdm import tqdm
import threading
import requests

# Initialize colorama
init(autoreset=True)

# Logging settings
logging.basicConfig(
    level=logging.INFO,
    filename='bitcoin_check.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize the API token and configuration
BLOCKCYPHER_TOKEN = "YOUR_BLOCKCYPHER_API_TOKEN"
OUTPUT_FILE = "bitcoin_addresses.txt"
BATCH_SIZE = 100  # Number of keys to process in a single batch
MAX_THREADS = 10  # Optimal number of concurrent threads

# Create a lock to ensure thread-safe file writing and logging
file_lock = threading.Lock()
console_lock = threading.Lock()

def generate_key_pair():
    """Generates a random private key and its corresponding Bitcoin address."""
    private_key = random_key()
    address = pubtoaddr(privtopub(private_key))
    return private_key, address

def check_balance(address, token):
    """Checks the balance of a Bitcoin address using the BlockCypher API."""
    url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance?token={token}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return address, response.json().get('final_balance', 0)
        elif response.status_code == 429:
            # Handle API rate limiting
            time.sleep(2)
            return check_balance(address, token)
        else:
            with console_lock:
                logging.error(f"API Error {response.status_code} for address {address}")
            return address, 0
    except Exception as e:
        with console_lock:
            logging.error(f"Network exception for address {address}: {e}")
        return address, 0

def save_address_to_file(private_key, address, balance, filename=OUTPUT_FILE):
    """Saves funded addresses to a .txt file safely using a lock."""
    with file_lock:
        with open(filename, 'a') as f:
            f.write(f"Private Key: {private_key} | Address: {address} | Balance: {balance}\n")

def process_batch():
    """Generates and checks a single batch of addresses."""
    key_pairs = [generate_key_pair() for _ in range(BATCH_SIZE)]
    results = []

    with console_lock:
        print(f"{Fore.CYAN}[*] Checking batch of {BATCH_SIZE} addresses...")

    with ThreadPoolExecutor(max_threads=MAX_THREADS) as executor:
        # Submit tasks and track which future corresponds to which private key
        future_to_key = {
            executor.submit(check_balance, address, BLOCKCYPHER_TOKEN): (private_key, address)
            for private_key, address in key_pairs
        }

        # Display progress using tqdm
        for future in tqdm(as_completed(future_to_key), total=BATCH_SIZE, desc="Processing", leave=False):
            private_key, address = future_to_key[future]
            try:
                addr, balance = future.result()
                results.append((private_key, addr, balance))
                
                # If a funded address is found, log it and save it
                if balance > 0:
                    with console_lock:
                        print(f"{Fore.GREEN}[+] FUND FOUND! Address: {address} | Balance: {balance}")
                    logging.info(f"FUND FOUND! Address: {address} | Balance: {balance}")
                    save_address_to_file(private_key, address, balance)
            except Exception as exc:
                with console_lock:
                    logging.error(f"{address} generated an exception: {exc}")

    with console_lock:
        print(f"{Fore.YELLOW}[*] Batch complete. Continuing...")

def main():
    print(f"{Fore.YELLOW}=== Bitcoin Address Generator & Checker Initialized ===")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop the script at any time.\n")
    
    if BLOCKCYPHER_TOKEN == "YOUR_BLOCKCYPHER_API_TOKEN":
        print(f"{Fore.RED}[!] WARNING: Please set your actual BlockCypher token in the script.")
    
    while True:
        try:
            process_batch()
            time.sleep(1)  # Brief pause between batches to prevent overwhelming the API
        except KeyboardInterrupt:
            print(f"{Fore.RED}\n[!] Script stopped by user.")
            break
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
