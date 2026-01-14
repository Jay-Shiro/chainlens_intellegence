from time import time
from fastapi import FastAPI, Query
import os
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

app = FastAPI(
    title="ChainLens API",
    description="Instant Web3 Wallet Intelligence",
    version="1.0.0"
)

@app.get("/")
def read_root():
    """
    Root endpoint to confirm API is running.
    """
    return {"message": "Welcome to the Delivery App API"}

# ============ CHAIN CONFIGURATION ============
CHAIN_CONFIG = {
    "ethereum": {
        "api": "https://api.etherscan.io/api",
        "key_env": "ETHERSCAN_API_KEY"
    },
    "base": {
        "api": "https://api.basescan.org/api",
        "key_env": "BASESCAN_API_KEY"
    },
    "arbitrum": {
        "api": "https://api.arbiscan.io/api",
        "key_env": "ARBISCAN_API_KEY"
    }
}

# Load API keys from environment variables
for chain in CHAIN_CONFIG:
    CHAIN_CONFIG[chain]['api_key'] = os.getenv(CHAIN_CONFIG[chain]['key_env'])

# ============ EXPLORERS ============
def get_transactions(address: str, chain: str, api_key: str):
    url = CHAIN_CONFIG[chain]["api"]
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "sort": "asc",
        "apikey": api_key
    }
    res = requests.get(url, params=params)
    return res.json()["result"]

def get_token_transfers(address: str, chain: str, api_key: str):
    url = CHAIN_CONFIG[chain]["api"]
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "sort": "asc",
        "apikey": api_key
    }
    res = requests.get(url, params=params)
    return res.json()["result"]

def wallet_age_days(transactions):
    first_tx = transactions[0]
    ts = int(first_tx["timeStamp"])
    return (datetime.utcnow() - datetime.utcfromtimestamp(ts)).days

# ============ ANALYZERS ============
def analyze_activity(transactions, token_transfers):
    dex_keywords = ["swap", "uniswap", "pancake", "router"]
    bridge_keywords = ["bridge", "hop", "stargate"]

    dex = 0
    bridge = 0

    for tx in transactions:
        input_data = tx["input"].lower()
        if any(k in input_data for k in dex_keywords):
            dex += 1
        if any(k in input_data for k in bridge_keywords):
            bridge += 1

    return {
        "dex_interactions": dex,
        "bridge_interactions": bridge,
        "nft_interactions": len(token_transfers)
    }

# ============ CLASSIFIERS ============
def generate_flags(age_days, activity, tx_30d):
    flags = []

    if age_days < 14:
        flags.append("FRESH_WALLET")

    if activity["dex_interactions"] > tx_30d * 0.6:
        flags.append("DEX_ACTIVE")

    if activity["bridge_interactions"] > 0:
        flags.append("BRIDGE_USER")

    if tx_30d > 100:
        flags.append("HIGH_ACTIVITY")

    return flags


@app.get("/api/v1/wallet/snapshot")
def wallet_snapshot(
    address: str = Query(...),
    chain: str = Query("ethereum")
):
    api_key = os.getenv("ETHERSCAN_API_KEY")

    txs = get_transactions(address, chain, api_key)
    tokens = get_token_transfers(address, chain, api_key)

    age = wallet_age_days(txs)
    activity = analyze_activity(txs, tokens)

    tx_30d = len([tx for tx in txs if int(tx["timeStamp"]) > (time.time() - 30*86400)])

    flags = generate_flags(age, activity, tx_30d)

    return {
        "wallet": {
            "address": address,
            "age_days": age,
            "total_tx": len(txs),
            "tx_30d": tx_30d
        },
        "activity": activity,
        "flags": flags
    }
