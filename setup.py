import os
import random
import requests
from bitcoin import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init
import logging
import time

# Initialize colorama
init(autoreset=True)

# Logging settings
logging.basicConfig(level=logging.INFO, filename='bitcoin_check.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Randomly generate a Bitcoin private key using 

def generate_private_key():
    # N is the max number of bitcoin private keys
    N = 115792089237316195423570985008687907853269984665640564039457584007913129639936
    private = random.randint(1, N)
    return private

# Convert private key to bitcoin address
def private_key_to_address(private_key):
    public_key = privtopub(private_key)
    address = pubtoaddr(public_key)
    return address

# Address inventory check using BlockCypher API
def check_balance(address, token):
    url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance?token={token}"
    response = requests.get(url)
    if response.status_code == 200:
        balance_data = response.json()
        return balance_data['final_balance']
    else:
        logging.error(f"Error checking balance for address {address}: {response.status_code}")
        return 0

# Enter your BlockCypher token here
blockcypher_token = "YOUR_BLOCKCYPHER_API_TOKEN"

def process_key():
    private_key = generate_private_key()
    address = private_key_to_address(private_key)
    balance = check_balance(address, blockcypher_token)

    # Output the private key, address, and balance with color
    balance_btc = balance / 1e8  # Convert Satoshi to Bitcoin
    print(f"{Fore.BLUE}{private_key} -> {Fore.GREEN}{address} {Fore.YELLOW}(Balance: {balance_btc} BTC)")
    logging.info(f"Processed address: {address} with balance: {balance_btc} BTC")

# Example execution to show how it ties together
if __name__ == "__main__":
    # Multi-threaded processing
    with ThreadPoolExecutor(max_workers=5) as executor:
        for _ in range(10):
            executor.submit(process_key)

