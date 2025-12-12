# src/services/web3_api.py
import os
import time
import requests
from typing import Optional, Dict, Any

# Simple in-memory TTL cache to reduce API calls
_cache: Dict[str, tuple] = {}
_CACHE_TTL = 60  # seconds; tune as needed for dev

def _get_cache(key: str):
    rec = _cache.get(key)
    if not rec:
        return None
    ts, val = rec
    if time.time() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return val

def _set_cache(key: str, val: Any):
    _cache[key] = (time.time(), val)


def get_moralis_api_key() -> Optional[str]:
    """Prefer Streamlit secrets, then environment variable."""
    try:
        import streamlit as st
        if "MORALIS_API_KEY" in st.secrets:
            return st.secrets["MORALIS_API_KEY"]
    except Exception:
        pass
    return os.environ.get("MORALIS_API_KEY")


# Mapping friendly chain names to Moralis chain param
# Moralis accepts things like 'eth', 'polygon', 'bsc', 'avalanche', 'fantom' etc.
CHAIN_MAP = {
    "ethereum": "eth",
    "eth": "eth",
    "polygon": "polygon",
    "matic": "polygon",
    "bsc": "bsc",
    "binance": "bsc",
    "avalanche": "avalanche",
    "fantom": "fantom",
    # add more as needed
}

def _normalize_chain(chain: str) -> str:
    if not chain:
        return "eth"
    return CHAIN_MAP.get(chain.lower(), chain.lower())


def _moralis_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generic Moralis GET with caching and error handling.
    endpoint may be a relative path like 'address/{address}/transactions' or a full URL.
    """
    key = get_moralis_api_key()
    if not key:
        return {"error": True, "reason": "no_api_key"}

    # If full URL passed, use it; else construct v2 base url
    if endpoint.lower().startswith("http"):
        url = endpoint
    else:
        url = f"https://deep-index.moralis.io/api/v2/{endpoint.lstrip('/')}"
    cache_key = f"moralis::{url}::{params}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    headers = {"Accept": "application/json", "X-API-Key": key}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        _set_cache(cache_key, data)
        return data
    except requests.RequestException as e:
        return {"error": True, "reason": "request_failed", "text": str(e)}
    except ValueError:
        return {"error": True, "reason": "json_decode_failed", "text": r.text if 'r' in locals() else ''}


# --- High-level helpers used by scorer.py ---

def get_address_transactions(chain: str, address: str, limit: int = 50) -> Any:
    """Return recent transactions list or error dict."""
    if not address:
        return {"error": True, "reason": "no_address"}
    ch = _normalize_chain(chain)
    endpoint = f"address/{address}/transactions"
    params = {"chain": ch, "limit": limit}
    return _moralis_get(endpoint, params=params)


def get_address_balance(chain: str, address: str) -> Any:
    """Return native balance; returns dict or error."""
    if not address:
        return {"error": True, "reason": "no_address"}
    ch = _normalize_chain(chain)
    endpoint = f"address/{address}/balance"
    return _moralis_get(endpoint, params={"chain": ch})


def get_address_erc20(chain: str, address: str) -> Any:
    """Return ERC20 token balances for address."""
    if not address:
        return {"error": True, "reason": "no_address"}
    ch = _normalize_chain(chain)
    endpoint = f"address/{address}/erc20"
    return _moralis_get(endpoint, params={"chain": ch})


def get_token_metadata(chain: str, token_address: str) -> Any:
    """Return token metadata via Moralis (erc20/metadata endpoint)."""
    if not token_address:
        return {}
    ch = _normalize_chain(chain)
    endpoint = "erc20/metadata"
    params = {"chain": ch, "addresses": token_address}
    res = _moralis_get(endpoint, params=params)
    # Moralis returns a list for metadata endpoint, try to normalize to dict
    if isinstance(res, list) and res:
        return res[0]
    return res


def get_token_price(chain: str, token_address: str) -> float:
    """Return token price in USD when available."""
    if not token_address:
        return 0.0
    ch = _normalize_chain(chain)
    endpoint = f"erc20/{token_address}/price"
    res = _moralis_get(endpoint, params={"chain": ch})
    if isinstance(res, dict):
        # Moralis variations: usdPrice or usd
        return float(res.get("usdPrice") or res.get("usd") or 0.0)
    return 0.0


def get_contract_metadata(chain: str, contract_address: str) -> Any:
    """Try Moralis contract metadata endpoint; may vary by region/version."""
    if not contract_address:
        return {}
    ch = _normalize_chain(chain)
    endpoint = f"contract/{contract_address}/metadata"
    return _moralis_get(endpoint, params={"chain": ch})
