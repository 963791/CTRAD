# src/scoring/scorer.py
import math
import time
from typing import Dict, Any, List
from src.services.web3_api import (
    get_address_balance,
    get_address_transactions,
    get_token_metadata,
    get_contract_verified_status,
)

# Static lists (you can extend these files / load from DB)
BLACKLIST = {
    "0xscamdead00000000000000000000000000000000",
    "0xphishdead000000000000000000000000000000",
}
RISKY_TOKENS = {"0xdeadtoken000000000000000000000000000000000"}  # add token contract addresses here

# rule weights (sum doesn't need to be 1; we'll normalize)
_RULE_POINTS = {
    "high_amount": 25,
    "fresh_wallet": 20,
    "blacklist": 30,
    "risky_token": 20,
    "rapid_spam": 15,
    "large_deviation": 20,
    "contract_unverified": 25,
    "dusting": 10,
    "self_transfer": 10,
    "odd_hour": 5,
}


def _norm_score(points: float, max_points: float = 100.0) -> float:
    """Normalize to 0..1"""
    return max(0.0, min(1.0, points / max_points))


class Scorer:
    """
    Rule-based scorer using Moralis lookups. Defensive: if Moralis returns error,
    the rule is skipped or downgraded.
    """

    def __init__(self):
        # Could load blacklist/token lists from file/DB
        self.blacklist = set(addr.lower() for addr in BLACKLIST)
        self.risky_tokens = set(tok.lower() for tok in RISKY_TOKENS)

    def _is_on_blacklist(self, addr: str) -> bool:
        if not addr:
            return False
        return addr.lower() in self.blacklist

    def score_pre_transaction(self, tx: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        tx: original transaction dict (chain, from_addr, to_addr, token_contract, amount_usd, timestamp)
        features: features from FeatureBuilder.transform_one (may be partial)
        """
        chain = tx.get("chain", "ethereum")
        from_addr = (tx.get("from_addr") or "").lower()
        to_addr = (tx.get("to_addr") or "").lower()
        token_contract = (tx.get("token_contract") or "").lower()
        amount_usd = float(tx.get("amount_usd") or 0.0)

        points = 0.0
        reasons: List[str] = []
        component_scores = {
            "rules": 0.0,
            "tabular": 0.0,
            "sequence": 0.0,
            "graph": 0.0,
            "contract": 0.0,
        }

        # --- Rule: blacklist
        try:
            if self._is_on_blacklist(to_addr) or self._is_on_blacklist(from_addr):
                points += _RULE_POINTS["blacklist"]
                reasons.append("address_on_blacklist")
                component_scores["rules"] = max(component_scores["rules"], _norm_score(_RULE_POINTS["blacklist"]))
        except Exception:
            pass

        # --- Rule: high amount
        try:
            if amount_usd >= 100000:
                points += _RULE_POINTS["high_amount"]
                reasons.append("very_high_amount")
            elif amount_usd >= 10000:
                points += _RULE_POINTS["high_amount"] * 0.6
                reasons.append("high_amount")
            elif amount_usd >= 1000:
                points += _RULE_POINTS["high_amount"] * 0.2
            component_scores["tabular"] = max(component_scores["tabular"], _norm_score(points))
        except Exception:
            pass

        # --- Rule: fresh wallet (use moralis txs if available)
        try:
            txs_to = get_address_transactions(chain, to_addr, limit=1)
            # Moralis returns list or error dict
            created_recent = False
            if isinstance(txs_to, dict) and txs_to.get("error"):
                # couldn't fetch; fall back to any feature if provided
                to_age_days = features.get("to_age_days")
                if to_age_days is not None and to_age_days < 30:
                    created_recent = True
            else:
                # if transactions list empty or first tx very recent, treat as fresh
                if isinstance(txs_to, list):
                    if not txs_to:
                        created_recent = True
                    else:
                        # if the first tx happened within <30 days
                        try:
                            first_ts = txs_to[0].get("block_timestamp") or txs_to[0].get("timestamp")
                            if first_ts:
                                from datetime import datetime, timezone
                                # Moralis timestamps often ISO strings
                                import dateutil.parser as dp
                                dt = dp.parse(first_ts)
                                age_days = (datetime.now(timezone.utc) - dt).days
                                if age_days < 30:
                                    created_recent = True
                        except Exception:
                            pass
            if created_recent:
                points += _RULE_POINTS["fresh_wallet"]
                reasons.append("recipient_fresh_wallet")
                component_scores["rules"] = max(component_scores["rules"], _norm_score(_RULE_POINTS["fresh_wallet"]))
        except Exception:
            pass

        # --- Rule: risky token (token contract in list)
        try:
            if token_contract and token_contract in self.risky_tokens:
                points += _RULE_POINTS["risky_token"]
                reasons.append("risky_token_contract")
                component_scores["contract"] = max(component_scores["contract"], _norm_score(_RULE_POINTS["risky_token"]))
        except Exception:
            pass

        # --- Rule: contract unverified (if sending to contract)
        try:
            if token_contract:
                cmeta = get_contract_verified_status(chain, token_contract)
                # Moralis may return dict with 'verified' or similar; if unknown, be conservative
                is_verified = False
                if isinstance(cmeta, dict):
                    # search common keys
                    if cmeta.get("verified") is True or cmeta.get("isVerified") is True:
                        is_verified = True
                if not is_verified and token_contract:
                    points += _RULE_POINTS["contract_unverified"]
                    reasons.append("contract_unverified_or_unverified_token")
                    component_scores["contract"] = max(component_scores["contract"], _norm_score(_RULE_POINTS["contract_unverified"]))
        except Exception:
            pass

        # --- Rule: self-transfer
        try:
            if from_addr and to_addr and from_addr == to_addr:
                points += _RULE_POINTS["self_transfer"]
                reasons.append("self_transfer_detected")
                component_scores["rules"] = max(component_scores["rules"], _norm_score(_RULE_POINTS["self_transfer"]))
        except Exception:
            pass

        # --- Rule: odd-hour (utc night)
        try:
            from datetime import datetime
            import dateutil.parser as dp
            ts = tx.get("timestamp")
            if ts:
                dt = dp.parse(ts)
                hour = dt.hour
            else:
                hour = datetime.utcnow().hour
            if hour < 3 or hour > 22:
                points += _RULE_POINTS["odd_hour"]
                reasons.append("odd_hour_transaction")
                component_scores["rules"] = max(component_scores["rules"], _norm_score(_RULE_POINTS["odd_hour"]))
        except Exception:
            pass

        # --- Rule: rapid spam / burst (look at sender recent txs)
        try:
            recent = get_address_transactions(chain, from_addr, limit=10)
            if isinstance(recent, list):
                # detect many txs in last hour
                from datetime import datetime, timezone
                import dateutil.parser as dp
                now = datetime.now(timezone.utc)
                cnt_1h = 0
                for r in recent:
                    ts = r.get("block_timestamp") or r.get("timestamp")
                    if not ts:
                        continue
                    dt = dp.parse(ts)
                    delta = (now - dt).total_seconds()
                    if delta < 3600:
                        cnt_1h += 1
                if cnt_1h >= 5:
                    points += _RULE_POINTS["rapid_spam"]
                    reasons.append("rapid_burst_from_sender")
                    component_scores["rules"] = max(component_scores["rules"], _norm_score(_RULE_POINTS["rapid_spam"]))
        except Exception:
            pass

        # --- Rule: dusting (very small amounts to many addresses)
        try:
            # If amount_usd is tiny (< $1) and sender has high out-degree, flag dusting possibility
            if amount_usd < 1:
                # check sender tx count in recent list
                recent = get_address_transactions(chain, from_addr, limit=50)
                if isinstance(recent, list) and len(recent) > 10:
                    points += _RULE_POINTS["dusting"]
                    reasons.append("possible_dusting_pattern")
                    component_scores["rules"] = max(component_scores["rules"], _norm_score(_RULE_POINTS["dusting"]))
        except Exception:
            pass

        # --- Rule: large deviation (compare to provided sender historical avg if available)
        try:
            sender_avg = features.get("sender_avg_tx_usd")
            if sender_avg is not None and sender_avg > 0:
                ratio = amount_usd / (sender_avg + 1e-9)
                if ratio >= 10:
                    points += _RULE_POINTS["large_deviation"]
                    reasons.append("amount_much_larger_than_sender_avg")
                    component_scores["tabular"] = max(component_scores["tabular"], _norm_score(_RULE_POINTS["large_deviation"]))
        except Exception:
            pass

        # Normalize total points to 0..100
        # The maximum possible points is sum of _RULE_POINTS values; use that to normalize
        max_possible = float(sum(_RULE_POINTS.values()))
        raw_score = points
        normalized = int(round((raw_score / max_possible) * 100, 2))
        # Cap 0..100
        risk_score = max(0, min(100, normalized))

        # Construct top_features list (prioritize blacklist / contract / amount)
        top_features = []
        for r in reasons:
            # simple impact heuristic
            impact = 0.5
            if r == "address_on_blacklist":
                impact = 0.9
            elif "high_amount" in r or "very_high" in r:
                impact = 0.8
            elif "contract_unverified" in r:
                impact = 0.7
            top_features.append({"feature": r, "value": True, "impact": impact})

        # If no reasons, mention conservative message
        reason_text = "; ".join(reasons) if reasons else "No immediate red flags detected (online checks OK)."

        # Suggested action thresholds:
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
            "raw_points": raw_score,
            "max_possible_points": max_possible,
        }
