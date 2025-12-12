from datetime import datetime

# Import rule-based model
from .rules import RuleEngine

# Import sequence anomaly model (Step 3)
from .sequence import SequenceModel


class Scorer:
    """
    CTRAD Scoring Engine
    Combines: rules, sequence anomaly, and placeholders for
    tabular ML, graph ML, and contract audits.
    """

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.sequence_model = SequenceModel()   # Step 3 model

    def score(self, params):
        """
        params: dictionary containing
        {
            "from_addr",
            "to_addr",
            "amount_usd",
            "token_symbol",
            "chain_id",
            "history_amounts": list of past amounts,
            ...
        }
        """

        amount_usd = params.get("amount_usd", 0)
        from_addr = params.get("from_addr", "")
        to_addr = params.get("to_addr", "")
        token = params.get("token_symbol", "")
        chain_id = params.get("chain_id", "")

        # -----------------------------
        # 1) RULE-BASED CHECKS (Step 1)
        # -----------------------------
        rule_label, rule_score, rule_reason = self.rule_engine.check(
            from_addr=from_addr,
            to_addr=to_addr,
            amount_usd=amount_usd,
            token_symbol=token
        )

        # -----------------------------------------
        # 2) SEQUENCE ANOMALY MODEL (Step 3)
        # -----------------------------------------
        sequence_risk = self.sequence_model.predict(
            history_amounts=params.get("history_amounts", []),
            current_amount=amount_usd
        )

        # ------------------------------------------------------
        # 3) Tabular ML model (placeholder — Step 4 will update)
        # ------------------------------------------------------
        tabular_risk = 0.10  # default placeholder

        # ------------------------------------------------------
        # 4) Graph ML (placeholder — Step 5 will update)
        # ------------------------------------------------------
        graph_risk = 0.0

        # ------------------------------------------------------
        # 5) Contract audit & flags (placeholder — Step 6)
        # ------------------------------------------------------
        contract_risk = 0.0

        # ---------------------------
        # Weighted Risk Combination
        # ---------------------------
        total_risk = (
            0.30 * rule_score +
            0.25 * sequence_risk +
            0.25 * tabular_risk +
            0.10 * graph_risk +
            0.10 * contract_risk
        )

        # Determine label
        if total_risk >= 0.70:
            label = "HIGH RISK"
        elif total_risk >= 0.40:
            label = "MEDIUM RISK"
        else:
            label = "SAFE"

        result = {
            "label": label,
            "overall_score": float(total_risk),

            "components": {
                "rules": float(rule_score),
                "sequence": float(sequence_risk),
                "tabular": float(tabular_risk),
                "graph": float(graph_risk),
                "contract": float(contract_risk),
            },

            "rule_reason": rule_reason,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return result
