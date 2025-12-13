# ============================================
# CTRAD — Ethereum Blockchain Client
# Step 7: Live On-Chain Data
# ============================================

import requests
import os
from datetime import datetime


class EthereumClient:
    """
    Lightweight Ethereum read-only client using Etherscan API.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY")
        self.base_url = "https://api.etherscan.io/api"

    # -------------------------------------------------
    # WALLET INFO
    # -------------------------------------------------
    def get_wallet_tx_count(self, address: str) -> int:
        """
        Returns total transaction count for a wallet.
        """
        params = {
            "module": "proxy",
            "action": "eth_getTransactionCount",
            "address": address,
            "tag": "latest",
            "apikey": self.api_key
        }

        try:
            r = requests.get(self.base_url, params=params, timeout=10)
            data = r.json()
            return int(data.get("result", "0x0"), 16)
        except Exception:
            return 0

    def get_wallet_age_days(self, address: str) -> int:
        """
        Approximate wallet age using first transaction.
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 1,
            "sort": "asc",
            "apikey": self.api_key
        }

        try:
            r = requests.get(self.base_url, params=params, timeout=10)
            txs = r.json().get("result", [])
            if not txs:
                return 0

            first_ts = int(txs[0]["timeStamp"])
            days = (datetime.utcnow().timestamp() - first_ts) / 86400
            return int(days)
        except Exception:
            return 0

    # -------------------------------------------------
    # CONTRACT INFO
    # -------------------------------------------------
    def is_contract_verified(self, contract_addr: str) -> bool:
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": contract_addr,
            "apikey": self.api_key
        }

        try:
            r = requests.get(self.base_url, params=params, timeout=10)
            result = r.json().get("result", [{}])[0]
            return bool(result.get("SourceCode"))
        except Exception:
            return False
