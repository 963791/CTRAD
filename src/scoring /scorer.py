# ================================
# CTRAD — SCORING ENGINE (FULL)
# ================================

from typing import Dict, List, Tuple
from .tabular import TabularModel


class CTRADScorer:
    """
    Main scoring engine combining:
    - Rule-based scoring
    - Sequence anomaly scoring
    - Tabular ML (RandomForest)
    - (Graph + Contract models added later)
    """

    def __init__(self):
        # ML model
        self.tabular_model = TabularModel()

    # ----------------------------
    # RULE ENGINE
    # ----------------------------
    def apply_rules(self, tx: dict) -> Tuple[float, List[str]]:
        amount = tx.get("amount_usd", 0)
        token = tx.get("token_symbol", "").upper()
        flags = []
        score = 0

        # Rule 1 — Large amount
        if amount > 10_000:
            score += 0.4
            flags.append("High-value transfer")
        elif amount > 5_000:
            score += 0.25
            flags.append("Medium-high value transfer")

        # Rule 2 — Risky tokens
        risky_tokens = {"SHIB", "PEPE", "FLOKI", "ELON", "SQUID", "LUNA2"}
        if token in risky_tokens:
            score += 0.35
            flags.append("High-volatility token")

        # Rule 3 — Unknown token (not common)
        common = {"ETH", "USDT", "USDC", "BNB", "BTC"}
        if token not in common and token not in risky_tokens:
            score += 0.05
            flags.append("Unrecognized token")

        # Cap score
        return min(score, 1.0), flags

    # ----------------------------
    # SEQUENCE ANOMALY MODEL
    # ----------------------------
    def sequence_anomaly(self, tx: dict) -> float:
        """
        Lightweight anomaly score.
        """
        amount = tx.get("amount_usd", 0)
        token = tx.get("token_symbol", "").upper()

        risk = 0.0

        # Spike behavior
        if amount > 3000:
            risk += 0.2
        if amount < 5:
            risk += 0.1

        # Volatile tokens
        volatile = {"DOGE", "SHIB", "PEPE"}
        if token in volatile:
            risk += 0.15

        return min(risk, 1.0)

    # ----------------------------
    # TABULAR ML MODEL (RandomForest)
    # ----------------------------
    def tabular_predict(self, tx: dict) -> float:
        return self.tabular_model.predict(
            amount_usd=tx.get("amount_usd", 0),
            token_symbol=tx.get("token_symbol", "ETH"),
            from_addr=tx.get("from_addr", "").lower()
        )

    # ----------------------------
    # COMBINE + FINAL SCORE
    # ----------------------------
    def aggregate_scores(
        self,
        rules: float,
        seq: float,
        tab: float
    ) -> float:
        """
        Weighted combination.
        """
        final = (
            0.45 * rules +
            0.25 * seq +
            0.30 * tab
        )
        return round(final * 100, 2)

    # ----------------------------
    # HUMAN-READABLE LABEL
    # ----------------------------
    def classify(self, score: float) -> str:
        if score >= 85:
            return "high-risk"
        elif score >= 60:
            return "medium-risk"
        else:
            return "safe"

    # ----------------------------
    # MAIN ENTRY (USED BY app.py)
    # ----------------------------
    def score_pre_transaction(self, tx: dict, features: dict = None) -> Dict:
        """
        Main scoring endpoint.
        tx: {
            from_addr,
            to_addr,
            token_symbol,
            amount_usd,
            ...
        }
        """

        # Component scores
        rules_score, rule_flags = self.apply_rules(tx)
        seq_score = self.sequence_anomaly(tx)
        tab_score = self.tabular_predict(tx)

        # Aggregate
        final_score = self.aggregate_scores(rules_score, seq_score, tab_score)
        label = self.classify(final_score)

        # Reason text
        if rule_flags:
            reason = ", ".join(rule_flags)
        else:
            reason = "No significant warnings."

        # Format top features
        top_features = [
            {"feature": "Rules engine", "value": "", "impact": round(rules_score, 3)},
            {"feature": "Sequence anomaly", "value": "", "impact": round(seq_score, 3)},
            {"feature": "Tabular ML model", "value": "", "impact": round(tab_score, 3)},
        ]

        # Component scores (for UI cards)
        components = {
            "rules": round(rules_score, 3),
            "sequence": round(seq_score, 3),
            "tabular": round(tab_score, 3),
            "graph": 0.0,
            "contract": 0.0
        }

        # Suggested action
        if final_score >= 85:
            action = "block"
        elif final_score >= 60:
            action = "warn"
        else:
            action = "allow"

        return {
            "risk_score": final_score,
            "risk_label": label,
            "component_scores": components,
            "top_features": top_features,
            "reason_text": reason,
            "action": action
        }
