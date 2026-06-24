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
            return response.json().get('final_balance', 0)
        elif response.status_code == 429:
            # Handle API rate limiting
            time.sleep(2)
            return check_balance(address, token)
        else:
            with console_lock:
                logging.error(f"API Error {response.status_code} for address {address}")
            return 0
    except Exception as e:
        with console_lock:
            logging.error(f"Network exception for address {address}: {e}")
        return 0

def save_address_to_file(address, balance, filename=OUTPUT_FILE):
    """Saves funded addresses to a .txt file safely using a lock."""
    with file_lock:
        with open(filename, "a") as file:
            file.write(f"Address: {address}, Balance: {balance} satoshis\n")

def process_single_key():
    """Generates a key, checks its balance, and returns results if funds exist."""
    private_key, address = generate_key_pair()
    balance = check_balance(address, BLOCKCYPHER_TOKEN)
    
    if balance > 0:
        save_address_to_file(address, balance)
        with console_lock:
            tqdm.write(f"{Fore.GREEN}[+] FUNDED ADDRESS FOUND! {Style.RESET_ALL}Address: {address} | Balance: {balance} satoshis")
            logging.info(f"Funded address found: {address} with {balance} satoshis")
    return balance

def run_batch_process():
    """Manages the batch execution using ThreadPoolExecutor and tqdm."""
    print(f"{Fore.CYAN}Starting batch processing of {BATCH_SIZE} keys...{Style.RESET_ALL}")
    
    funded_count = 0
    with ThreadPoolExecutor(max_threads=MAX_THREADS) as executor:
        # Submit all tasks for the batch size
        futures = [executor.submit(process_single_key) for _ in range(BATCH_SIZE)]
        
        # Display a progress bar for the batch execution
        with tqdm(total=BATCH_SIZE, desc="Processing keys") as pbar:
            for future in as_completed(futures):
                try:
                    balance = future.result()
                    if balance > 0:
                        funded_count += 1
                except Exception as e:
                    with console_lock:
                        logging.error(f"Thread execution error: {e}")
                pbar.update(1)
                
    print(f"{Fore.CYAN}Batch processing complete. Total funded addresses found: {funded_count}{Style.RESET_ALL}")

if __name__ == "__main__":
    run_batch_process()
