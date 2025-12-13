# =====================================================
# CTRAD — Pre-Transaction Risk & Anomaly Scoring Engine
# Industry-Grade (Steps 1–7)
# =====================================================

from src.graph.graph_reputation import GraphReputation
from src.contract.contract_risk import ContractRiskEngine
from src.chain.eth_client import EthereumClient


class CTRADScorer:
    """
    Multi-layer crypto transaction risk engine.
    Uses rules, heuristics, graph intelligence,
    smart-contract checks, and LIVE blockchain data.
    """

    def __init__(self):
        self.graph_model = GraphReputation()
        self.contract_engine = ContractRiskEngine()
        self.eth_client = EthereumClient()

    # -------------------------------------------------
    # MAIN ENTRY POINT
    # -------------------------------------------------
    def score_pre_transaction(self, tx: dict, features: dict = None) -> dict:
        """
        tx: transaction-level inputs from UI
        """

        # ================================
        # STEP 7 — LIVE BLOCKCHAIN FEATURES
        # ================================
        from_addr = tx.get("from_addr", "")

        wallet_tx_count = self.eth_client.get_wallet_tx_count(from_addr)
        wallet_age_days = self.eth_client.get_wallet_age_days(from_addr)

        # enrich tx dict
        tx["wallet_tx_count"] = wallet_tx_count
        tx["wallet_age_days"] = wallet_age_days

        # ================================
        # STEP 1 — RULE-BASED CHECKS
        # ================================
        rules_score, rules_reason = self.rule_based_checks(tx)

        # ================================
        # STEP 2 — TABULAR HEURISTICS
        # ================================
        tab_score = self.tabular_score(tx)

        # ================================
        # STEP 3 — SEQUENCE / BEHAVIOR
        # ================================
        seq_score = self.sequence_score(tx)

        # ================================
        # STEP 5 — GRAPH REPUTATION
        # ================================
        graph_score = self.graph_model.score(from_addr)

        # ================================
        # STEP 6 — CONTRACT RISK
        # ================================
        contract_addr = tx.get("contract_addr", "")
        contract_score, contract_reasons = self.contract_engine.score(
            contract_addr, tx
        )

        # ================================
        # FINAL AGGREGATION
        # ================================
        final_score = self.aggregate_scores(
            rules_score,
            seq_score,
            tab_score,
            graph_score,
            contract_score
        )

        label, action = self.map_label_action(final_score)

        return {
            "risk_score": final_score,
            "risk_label": label,
            "action": action,
            "reason_text": (
                "; ".join(contract_reasons)
                if contract_reasons
                else rules_reason
            ),
            "component_scores": {
                "rules": round(rules_score, 3),
                "tabular": round(tab_score, 3),
                "sequence": round(seq_score, 3),
                "graph": round(graph_score, 3),
                "contract": round(contract_score, 3)
            },
            "top_features": self.top_features(tx, tab_score)
        }

    # -------------------------------------------------
    # STEP 1 — RULE-BASED DETECTION
    # -------------------------------------------------
    def rule_based_checks(self, tx: dict):
        score = 0.0
        reasons = []

        amount = float(tx.get("amount_usd", 0))
        token = tx.get("token_symbol", "").upper()
        to_addr = tx.get("to_addr", "").lower()

        if amount >= 100_000:
            score += 0.7
            reasons.append("Very high transaction amount")

        if token in {"UNKNOWN", "SCAM", "FAKE"}:
            score += 0.6
            reasons.append("Suspicious token symbol")

        if to_addr.startswith("0x000"):
            score += 0.8
            reasons.append("Blacklisted destination address pattern")

        return min(score, 1.0), (
            "; ".join(reasons) if reasons else "No major rule violations"
        )

    # -------------------------------------------------
    # STEP 2 — TABULAR HEURISTICS
    # -------------------------------------------------
    def tabular_score(self, tx: dict):
        amount = float(tx.get("amount_usd", 0))

        if amount < 500:
            return 0.05
        elif amount < 5_000:
            return 0.15
        elif amount < 25_000:
            return 0.35
        elif amount < 100_000:
            return 0.6
        else:
            return 0.9

    # -------------------------------------------------
    # STEP 3 — SEQUENCE / WALLET BEHAVIOR (LIVE)
    # -------------------------------------------------
    def sequence_score(self, tx: dict):
        tx_count = tx.get("wallet_tx_count", 0)
        wallet_age = tx.get("wallet_age_days", 0)

        score = 0.0

        if tx_count < 5:
            score += 0.4  # very new wallet

        if wallet_age < 7:
            score += 0.5  # newly created wallet

        return min(score, 1.0)

    # -------------------------------------------------
    # FINAL AGGREGATION
    # -------------------------------------------------
    def aggregate_scores(self, rules, seq, tab, graph, contract):
        score = (
            0.30 * rules +
            0.20 * seq +
            0.20 * tab +
            0.15 * graph +
            0.15 * contract
        )
        return round(score * 100, 2)

    # -------------------------------------------------
    # LABEL & ACTION
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
            },
            {
                "feature": "wallet_tx_count",
                "value": tx.get("wallet_tx_count", 0),
                "impact": round(self.sequence_score(tx), 3)
            }
        ]
