# ============================================
# CTRAD — Smart Contract Risk Engine
# ============================================

class ContractRiskEngine:
    """
    Detects malicious token contract patterns.
    Industry-inspired heuristics (static analysis style).
    """

    def __init__(self):
        # Demo blacklist (replace with real API later)
        self.blacklisted_contracts = {
            "0xdeadbeef",
            "0xbadhoneypot",
            "0xscamtoken"
        }

    def score(self, contract_addr: str, tx: dict) -> tuple:
        """
        Returns:
        (risk_score 0–1, reasons list)
        """

        if not contract_addr:
            return 0.0, ["No contract address provided"]

        contract_addr = contract_addr.lower()
        score = 0.0
        reasons = []

        # 1️⃣ Blacklist check
        if contract_addr in self.blacklisted_contracts:
            score += 0.9
            reasons.append("Contract is blacklisted")

        # 2️⃣ Suspicious token naming
        symbol = tx.get("token_symbol", "").upper()
        if symbol in {"USDT", "ETH", "BTC"}:
            score += 0.4
            reasons.append("Popular token symbol but unknown contract")

        # 3️⃣ Honeypot heuristic (simplified)
        sell_tax = tx.get("sell_tax", 0)
        buy_tax = tx.get("buy_tax", 0)

        if sell_tax and sell_tax > 20:
            score += 0.6
            reasons.append("Very high sell tax (possible honeypot)")

        if buy_tax and buy_tax > 15:
            score += 0.4
            reasons.append("High buy tax")

        # 4️⃣ Ownership control
        owner = tx.get("contract_owner", "")
        if owner and owner != "renounced":
            score += 0.3
            reasons.append("Contract ownership not renounced")

        return min(score, 1.0), reasons
