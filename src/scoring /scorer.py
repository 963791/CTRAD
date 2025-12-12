import joblib
import numpy as np
import os

# inside Scorer.__init__(self):
try:
    self.lgbm = joblib.load('models/model_lgbm_v1.pkl')
    self.fb = joblib.load('models/feature_builder_v1.pkl')
    self.has_lgbm = True
except Exception:
    self.lgbm = None
    self.fb = None
    self.has_lgbm = False

# create a helper to get tabular probability
def tabular_prob(self, tx: Dict[str, Any], features: Dict[str, Any]) -> float:
    # features: can be used, but better to use stored fb to create same columns
    try:
        if self.has_lgbm and self.fb:
            # Build a single-row dataframe using fb
            df_row = pd.DataFrame([tx])  # include amount_usd, token_contract, etc
            Xrow = self.fb.transform(df_row)
            # select numeric features used in training; fallback to amount_usd
            numeric_cols = [c for c in Xrow.columns if np.issubdtype(Xrow[c].dtype, np.number)]
            if not numeric_cols:
                return 0.0
            Xrow = Xrow[numeric_cols].fillna(0.0)
            prob = float(self.lgbm.predict(Xrow)[0])
            return max(0.0, min(1.0, prob))
    except Exception:
        pass
    # fallback heuristic mapping (similar to previously)
    amt = float(tx.get('amount_usd') or 0.0)
    if amt <= 1000:
        return 0.05
    elif amt <= 10000:
        return 0.2
    elif amt <= 100000:
        return 0.5
    else:
        return 0.85


# src/scoring/scorer.py
import math
from typing import Dict, Any, List
from src.services.web3_api import (
    get_address_transactions,
    get_address_erc20,
    get_token_metadata,
    get_token_price,
    get_contract_metadata,
)

# Extend these sets with your own data (or load from DB/files)
BLACKLIST = {
    "0xscamdead00000000000000000000000000000000",
    "0xphishdead000000000000000000000000000000",
}
RISKY_TOKENS = {
    "0xdeadtoken000000000000000000000000000000000"
}

# Rule scoring weights (points)
_RULE_POINTS = {
    "blacklist": 30,
    "high_amount": 25,
    "fresh_wallet": 20,
    "risky_token": 20,
    "contract_unverified": 25,
    "rapid_spam": 15,
    "large_deviation": 20,
    "dusting": 10,
    "self_transfer": 10,
    "odd_hour": 5,
}

def _norm(v: float, max_points: float) -> float:
    return max(0.0, min(1.0, v / max_points))

class Scorer:
    def __init__(self):
        self.blacklist = set(a.lower() for a in BLACKLIST)
        self.risky_tokens = set(t.lower() for t in RISKY_TOKENS)

    def _is_blacklisted(self, addr: str) -> bool:
        return bool(addr) and addr.lower() in self.blacklist

    def score_pre_transaction(self, tx: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        tx: dict with keys: chain, from_addr, to_addr, token_contract, amount_usd, timestamp
        features: optional precomputed fields (sender_avg, to_age_days, etc.)
        """
        chain = tx.get("chain", "ethereum")
        from_addr = (tx.get("from_addr") or "").lower()
        to_addr = (tx.get("to_addr") or "").lower()
        token_contract = (tx.get("token_contract") or "").lower()
        amount_usd = float(tx.get("amount_usd") or 0.0)

        points = 0.0
        reasons: List[str] = []
        component_scores = {"rules": 0.0, "tabular": 0.0, "sequence": 0.0, "graph": 0.0, "contract": 0.0}

        # 1) Blacklist check (immediate high risk)
        try:
            if self._is_blacklisted(to_addr) or self._is_blacklisted(from_addr):
                points += _RULE_POINTS["blacklist"]
                reasons.append("address_on_blacklist")
                component_scores["rules"] = max(component_scores["rules"], _norm(_RULE_POINTS["blacklist"], _RULE_POINTS["blacklist"]))
        except Exception:
            pass

        # 2) High amount thresholds
        try:
            if amount_usd >= 100000:
                points += _RULE_POINTS["high_amount"]
                reasons.append("very_high_amount")
            elif amount_usd >= 10000:
                points += _RULE_POINTS["high_amount"] * 0.6
                reasons.append("high_amount")
            elif amount_usd >= 1000:
                points += _RULE_POINTS["high_amount"] * 0.2
            component_scores["tabular"] = max(component_scores["tabular"], _norm(points, sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 3) Fresh recipient wallet (use Moralis tx history if available)
        try:
            txs_to = get_address_transactions(chain, to_addr, limit=1)
            fresh = False
            if isinstance(txs_to, dict) and txs_to.get("error"):
                # fallback to provided feature if exists
                to_age_days = features.get("to_age_days")
                if to_age_days is not None and to_age_days < 30:
                    fresh = True
            else:
                # Moralis returns list; if empty -> newly observed address
                if isinstance(txs_to, list):
                    if not txs_to:
                        fresh = True
                    else:
                        # parse first tx timestamp to compute age
                        try:
                            ts = txs_to[0].get("block_timestamp") or txs_to[0].get("timestamp")
                            if ts:
                                import dateutil.parser as dp
                                from datetime import datetime, timezone
                                dt = dp.parse(ts)
                                age_days = (datetime.now(timezone.utc) - dt).days
                                if age_days < 30:
                                    fresh = True
                        except Exception:
                            pass
            if fresh:
                points += _RULE_POINTS["fresh_wallet"]
                reasons.append("recipient_fresh_wallet")
                component_scores["rules"] = max(component_scores["rules"], _norm(_RULE_POINTS["fresh_wallet"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 4) Risky token list
        try:
            if token_contract and token_contract in self.risky_tokens:
                points += _RULE_POINTS["risky_token"]
                reasons.append("token_in_risky_list")
                component_scores["contract"] = max(component_scores["contract"], _norm(_RULE_POINTS["risky_token"], sum(_RULE_POINTS.values())))
            else:
                # Lookup token metadata and price to detect very low liquidity tokens (best-effort)
                if token_contract:
                    meta = get_token_metadata(chain, token_contract)
                    # Basic heuristic: if totalSupply is small or missing, mark suspicion
                    tsupply = None
                    if isinstance(meta, dict):
                        tsupply = meta.get("totalSupply") or meta.get("supply") or None
                    # price check
                    price = get_token_price(chain, token_contract)
                    # if price missing or zero, potentially suspicious (but don't overflag)
                    if price == 0.0 and meta:
                        # small suspicion - minor points
                        points += 2
                        reasons.append("token_price_unavailable_or_zero")
        except Exception:
            pass

        # 5) Contract unverified (if sending to contract address)
        try:
            if token_contract:
                cmeta = get_contract_metadata(chain, token_contract)
                is_verified = False
                if isinstance(cmeta, dict) and (cmeta.get("verified") is True or cmeta.get("isVerified") is True):
                    is_verified = True
                if not is_verified:
                    points += _RULE_POINTS["contract_unverified"]
                    reasons.append("contract_unverified")
                    component_scores["contract"] = max(component_scores["contract"], _norm(_RULE_POINTS["contract_unverified"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 6) Self-transfer
        try:
            if from_addr and to_addr and from_addr == to_addr:
                points += _RULE_POINTS["self_transfer"]
                reasons.append("self_transfer")
                component_scores["rules"] = max(component_scores["rules"], _norm(_RULE_POINTS["self_transfer"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 7) Odd hour (UTC)
        try:
            import dateutil.parser as dp
            from datetime import datetime
            ts = tx.get("timestamp")
            if ts:
                dt = dp.parse(ts)
                hr = dt.hour
            else:
                hr = datetime.utcnow().hour
            if hr < 3 or hr > 22:
                points += _RULE_POINTS["odd_hour"]
                reasons.append("odd_hour_tx")
                component_scores["rules"] = max(component_scores["rules"], _norm(_RULE_POINTS["odd_hour"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 8) Rapid spam / burst detection (sender recent txs)
        try:
            recent = get_address_transactions(chain, from_addr, limit=20)
            if isinstance(recent, list):
                import dateutil.parser as dp
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                cnt_1h = 0
                for r in recent:
                    ts = r.get("block_timestamp") or r.get("timestamp")
                    if not ts:
                        continue
                    dt = dp.parse(ts)
                    if (now - dt).total_seconds() < 3600:
                        cnt_1h += 1
                if cnt_1h >= 5:
                    points += _RULE_POINTS["rapid_spam"]
                    reasons.append("rapid_sender_burst")
                    component_scores["rules"] = max(component_scores["rules"], _norm(_RULE_POINTS["rapid_spam"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 9) Dusting: tiny amount to many addresses
        try:
            if amount_usd < 1:
                recent = get_address_transactions(chain, from_addr, limit=50)
                if isinstance(recent, list) and len(recent) > 10:
                    points += _RULE_POINTS["dusting"]
                    reasons.append("possible_dusting")
                    component_scores["rules"] = max(component_scores["rules"], _norm(_RULE_POINTS["dusting"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # 10) Large deviation from sender average (if features provide sender_avg_tx_usd)
        try:
            sender_avg = features.get("sender_avg_tx_usd")
            if sender_avg:
                ratio = amount_usd / (sender_avg + 1e-9)
                if ratio >= 10:
                    points += _RULE_POINTS["large_deviation"]
                    reasons.append("amount_much_larger_than_sender_avg")
                    component_scores["tabular"] = max(component_scores["tabular"], _norm(_RULE_POINTS["large_deviation"], sum(_RULE_POINTS.values())))
        except Exception:
            pass

        # Normalize to 0..100 based on max possible points
        max_points = float(sum(_RULE_POINTS.values()))
        risk_score = int(round((points / max_points) * 100, 2))
        risk_score = max(0, min(100, risk_score))

        # Build top_features list for UI (prioritize blacklist, amount, contract)
        top_features = []
        for r in reasons:
            impact = 0.5
            if r == "address_on_blacklist":
                impact = 0.95
            elif "high_amount" in r:
                impact = 0.8
            elif "contract_unverified" in r:
                impact = 0.7
            top_features.append({"feature": r, "value": True, "impact": impact})

        reason_text = "; ".join(reasons) if reasons else "No immediate red flags detected (online checks OK)."

        action = "allow"
        if risk_score >= 85:
            action = "block"
        elif risk_score >= 60:
            action = "warn"

        return {
            "risk_score": risk_score,
            "risk_label": ("high_risk" if risk_score >= 85 else ("suspicious" if risk_score >= 60 else "safe")),
            "component_scores": {k: round(v, 3) for k, v in component_scores.items()},
            "top_features": top_features,
            "reason_text": reason_text,
            "action": action,
            "raw_points": points,
            "max_possible_points": max_points,
        }
