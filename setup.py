import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bitcoin import *
from colorama import Fore, Style, init
from tqdm import tqdm

# Initialize colorama
init(autoreset=True)

# Logging settings
logging.basicConfig(
    level=logging.INFO,
    filename='bitcoin_check.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize the API token
BLOCKCYPHER_TOKEN = "YOUR_BLOCKCYPHER_API_TOKEN"
OUTPUT_FILE = "bitcoin_addresses.txt"
BATCH_SIZE = 100  # Number of keys to process in a single batch

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
            logging.error(f"API Error {response.status_code} for address {address}")
            return 0
    except Exception as e:
        logging.error(f"Network exception for address {address}: {e}")
        return 0

def save_address_to_file(address, balance, filename=OUTPUT_FILE):
    """Saves funded addresses to a .txt file."""
    with open(filename, "a") as file:
        file.write(f"Address: {address}, Balance: {balance} satoshis\n")

def process_single_key():
    """Generates a key, checks its balance, and returns results if funds exist."""
    private_key, address = generate_key_pair()
    balance = check_balance(address, BLOCKCYPHER_TOKEN)
    return private_key, address, balance

def main():
    max_workers = 10  # Adjust concurrency based on API rate limits
    
    print(f"{Fore.CYAN}Starting key generation... {Fore.YELLOW}(Press Ctrl+C to stop)")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # TQDM progress wrapper for the infinite loop
        with tqdm(total=0, unit="keys", dynamic_ncols=True, desc="Processing") as pbar:
            while True:
                futures = [executor.submit(process_single_key) for _ in range(BATCH_SIZE)]
                
                for future in as_completed(futures):
                    pbar.update(1)
                    private_key, address, balance = future.result()
                    
                    if balance > 0:
                        balance_btc = balance / 1e8
                        save_address_to_file(address, balance)
                        print(f"\n{Fore.RED}[FOUND] {Fore.BLUE}{private_key} -> "
                              f"{Fore.GREEN}{address} {Fore.YELLOW}(Balance: {balance_btc} BTC)")
                        logging.info(f"FOUND - Address: {address}, Balance: {balance} satoshis")
                    else:
                        logging.info(f"Generated address: {address}")

if __name__ == "__main__":
    main()
