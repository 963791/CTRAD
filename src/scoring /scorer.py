# ============================================
# CTRAD — Pre-Transaction Risk Scoring Engine
# ============================================

from src.graph.graph_reputation import GraphReputation


class CTRADScorer:
    """
    Core scoring engine for CTRAD.
    Combines multiple weak signals into a strong final risk score.
    """

    def __init__(self):
        self.graph_model = GraphReputation()

    # -------------------------------------------------
    # MAIN ENTRY POINT
    # -------------------------------------------------
    def score_pre_transaction(self, tx: dict, features: dict = None) -> dict:
        """
        tx: transaction-level inputs from UI
        features: optional precomputed features
        """

        # 1️⃣ Rule-based checks
        rules_score, rules_reason = self.rule_based_checks(tx)

        # 2️⃣ Tabular risk (amount, token, heuristics)
        tab_score = self.tabular_score(tx)

        # 3️⃣ Sequence score (history-based placeholder)
        seq_score = self.sequence_score(tx)

        # 4️⃣ Graph-based wallet reputation (NEW)
        graph_score = self.graph_model.score(tx.get("from_addr", ""))

        # 5️⃣ Aggregate final risk
        final_score = self.aggregate_scores(
            rules_score, seq_score, tab_score, graph_score
        )

        # 6️⃣ Label & action
        label, action = self.map_label_action(final_score)

        # 7️⃣ Build response
        return {
            "risk_score": final_score,
            "risk_label": label,
            "action": action,
            "reason_text": rules_reason,
            "component_scores": {
                "rules": round(rules_score, 3),
                "tabular": round(tab_score, 3),
                "sequence": round(seq_score, 3),
                "graph": round(graph_score, 3),
                "contract": 0.0  # placeholder for Step 6
            },
            "top_features": self.top_features(tx, tab_score),
        }

    # -------------------------------------------------
    # RULE-BASED ENGINE (STEP 1)
    # -------------------------------------------------
    def rule_based_checks(self, tx: dict):
        score = 0.0
        reasons = []

        amount = float(tx.get("amount_usd", 0))
        token = tx.get("token_symbol", "").upper()
        to_addr = tx.get("to_addr", "").lower()

        if amount >= 100000:
            score += 0.7
            reasons.append("Very high transaction amount")

        if token in {"UNKNOWN", "SCAM", "FAKE"}:
            score += 0.6
            reasons.append("Suspicious token symbol")

        if to_addr.startswith("0x000"):
            score += 0.8
            reasons.append("Blacklisted destination pattern")

        return min(score, 1.0), (
            "; ".join(reasons) if reasons else "No major rule violations"
        )

    # -------------------------------------------------
    # TABULAR HEURISTICS (STEP 2)
    # -------------------------------------------------
    def tabular_score(self, tx: dict):
        amount = float(tx.get("amount_usd", 0))

        if amount < 500:
            return 0.05
        elif amount < 5000:
            return 0.15
        elif amount < 25000:
            return 0.35
        elif amount < 100000:
            return 0.6
        else:
            return 0.9

    # -------------------------------------------------
    # SEQUENCE / BEHAVIOR (STEP 3)
    # -------------------------------------------------
    def sequence_score(self, tx: dict):
        """
        Placeholder for wallet history modeling.
        Later replace with LSTM / HMM / time-based logic.
        """
        return 0.1

    # -------------------------------------------------
    # AGGREGATION (STEP 5)
    # -------------------------------------------------
    def aggregate_scores(self, rules, seq, tab, graph):
        """
        Weighted ensemble aggregation
        Output scaled to 0–100
        """
        score = (
            0.35 * rules +
            0.25 * seq +
            0.25 * tab +
            0.15 * graph
        )
        return round(score * 100, 2)

    # -------------------------------------------------
    # LABEL + ACTION
    # -------------------------------------------------
    def map_label_action(self, score: float):
        if score >= 85:
            return "HIGH_RISK", "block"
        elif score >= 60:
            return "MEDIUM_RISK", "warn"
        else:
            return "SAFE", "allow"

    # -------------------------------------------------
    # FEATURE EXPLANATION
    # -------------------------------------------------
    def top_features(self, tx: dict, tab_score: float):
        return [
            {
                "feature": "amount_usd",
                "value": float(tx.get("amount_usd", 0)),
                "impact": round(tab_score, 3)
            }
        ]
