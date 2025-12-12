# src/services/web3_api.py
import os
import time
import requests
from typing import Optional, Dict, Any

# Optional simple caching for repeated calls (in-memory)
_cache = {}
_CACHE_TTL = 60  # seconds; tune as needed

def _get_from_cache(key):
    rec = _cache.get(key)
    if not rec:
        return None
    ts, val = rec
    if time.time() - ts > _CACHE_TTL:
        try:
            del _cache[key]
        except KeyError:
            pass
        return None
    return val

def _set_cache(key, val):
    _cache[key] = (time.time(), val)

def get_moralis_api_key():
    # Prefer Streamlit secrets, otherwise environment variable, otherwise None
    try:
        import streamlit as st
        if "MORALIS_API_KEY" in st.secrets:
            return st.secrets["MORALIS_API_KEY"]
    except Exception:
        pass
    # fallback to env
    return os.environ.get("MORALIS_API_KEY")


def moralis_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generic GET to Moralis REST v2 (or full URL if you pass it).
    The Moralis key is read from st.secrets['MORALIS_API_KEY'] or env var.
    """
    key = get_moralis_api_key()
    if not key:
        raise RuntimeError("Moralis API key not found. Set st.secrets['MORALIS_API_KEY'] or env var MORALIS_API_KEY")

    # If endpoint looks like full url, use it; otherwise use v2 base
    if endpoint.lower().startswith("http"):
        url = endpoint
    else:
        # NOTE: Moralis base URL may be region-specific; this uses the standard header approach
        url = f"https://deep-index.moralis.io/api/v2/{endpoint.lstrip('/')}"
    cache_key = f"moralis:{url}:{params}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    headers = {
        "Accept": "application/json",
        "X-API-Key": key
    }
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as e:
        # return empty dict on error to keep app resilient
        return {"error": True, "status_code": resp.status_code, "text": resp.text}

    data = resp.json()
    _set_cache(cache_key, data)
    return data


# --- Helpers used by scorer ---

def get_address_balance(chain: str, address: str) -> Dict[str, Any]:
    """
    Returns ERC20 balances and native balance from Moralis endpoint.
    Endpoint: /{address}/balance  and /{address}/erc20
    """
    # native balance
    native = moralis_get(f"address/{address}/balance", params={"chain": chain})
    # erc20 tokens
    erc20 = moralis_get(f"address/{address}/erc20", params={"chain": chain})
    return {"native": native, "erc20": erc20}


def get_token_metadata(chain: str, token_address: str) -> Dict[str, Any]:
    """
    Query token metadata (name, symbol, decimals, totalSupply if available)
    Moralis: /erc20/metadata or /erc20/{address}/metadata (some endpoints vary)
    """
    if not token_address:
        return {}
    # new Moralis supports: /erc20/metadata?addresses=0x...,chain=...
    data = moralis_get("erc20/metadata", params={"chain": chain, "addresses": token_address})
    # returns list
    if isinstance(data, list) and data:
        return data[0]
    return data


def get_address_transactions(chain: str, address: str, limit: int = 10) -> Any:
    """
    Get recent transactions for an address (Moralis: /{address})
    """
    return moralis_get(f"address/{address}/transactions", params={"chain": chain, "limit": limit})


def get_token_price_usd(chain: str, token_address: str) -> float:
    """
    Query token price; Moralis provides token price endpoints in some regions.
    """
    data = moralis_get(f"erc20/{token_address}/price", params={"chain": chain})
    # data may have usdPrice
    if isinstance(data, dict):
        return data.get("usdPrice") or data.get("usd")
    return 0.0


def get_contract_verified_status(chain: str, address: str) -> Dict[str, Any]:
    """
    Placeholder: Moralis has /contract/{address}/metadata or you can use Etherscan.
    We'll try a Moralis contract endpoint; fallback returns empty.
    """
    if not address:
        return {}
    return moralis_get(f"contract/{address}/metadata", params={"chain": chain})
