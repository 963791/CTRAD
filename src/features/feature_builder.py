# src/features/feature_builder.py
import datetime


class FeatureBuilder:
"""Lightweight FeatureBuilder for pre-transaction context.
This computes only features available before broadcasting a tx.
Replace / extend with real historical queries in production.
"""
def __init__(self):
# load any global stats or cached DB here (placeholder)
pass


def transform_one(self, tx: dict) -> dict:
# tx: dict with keys chain, from_addr, to_addr, amount, amount_usd, timestamp
feat = {}
# Basic
feat['amount_usd'] = float(tx.get('amount_usd', 0.0) or 0.0)
feat['log_amount'] = float((feat['amount_usd'] + 1.0))
# Mock address history features (in real app query DB or node)
# For demo create simple heuristics
feat['from_age_days'] = 400 # assume older address
feat['to_age_days'] = 1 if tx['to_addr'].endswith('dead') else 120
feat['sender_tx_count_7d'] = 5
feat['recipient_tx_count_7d'] = 1
feat['is_contract_to'] = tx.get('token_contract', '') != ''
return feat


def fit(self, records):
# Optionally implement if you need global statistics
return self
