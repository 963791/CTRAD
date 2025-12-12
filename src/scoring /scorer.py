# src/scoring/score.py

def rule_based_score(transaction):
    """
    Apply rule-based checks and return:
    - score (0–1)
    - reasons (list of triggered rule messages)
    """

    reasons = []
    score = 0.0

    amount = float(transaction.get("amount_usd", 0))
    txn_type = transaction.get("transaction_type", "").lower()
    wallet = transaction.get("wallet_age_days", 9999)
    country = transaction.get("origin_country", "")
    freq = transaction.get("daily_txn_count", 0)

    # ---- RULE 1: High Transaction Amount ----
    if amount > 10000:
        score += 0.6
        reasons.append(f"High-value transaction: ${amount}")

    elif amount > 5000:
        score += 0.3
        reasons.append(f"Medium-risk amount: ${amount}")

    # ---- RULE 2: Suspicious Transaction Types ----
    suspicious_types = ["mixing", "anonymizer", "privacy"]
    if txn_type in suspicious_types:
        score += 0.4
        reasons.append(f"Suspicious transaction type detected: {txn_type}")

    # ---- RULE 3: Very New Wallet ----
    if wallet < 7:
        score += 0.4
        reasons.append(f"New wallet age: {wallet} days")

    elif wallet < 30:
        score += 0.2
        reasons.append(f"Wallet is new-ish: {wallet} days")

    # ---- RULE 4: High Transaction Frequency ----
    if freq > 20:
        score += 0.5
        reasons.append(f"High daily transaction count: {freq}")

    elif freq > 10:
        score += 0.2
        reasons.append(f"Increased daily transaction activity: {freq}")

    # ---- RULE 5: High-Risk Country ----
    risky_countries = ["North Korea", "Russia", "Iran"]
    if country in risky_countries:
        score += 0.5
        reasons.append(f"High-risk country detected: {country}")

    # ---- Final score clamp ----
    score = min(score, 1.0)

    return score, reasons



def combine_scores(rule_score, tab_score=0, seq_score=0, graph_score=0):
    """
    Weighted score combination.
    Modify weights here as ML models are added.
    """

    weights = {
        "rules": 0.6,
        "tabular": 0.2,
        "sequence": 0.1,
        "graph": 0.1,
    }

    combined = (
        rule_score * weights["rules"]
        + tab_score * weights["tabular"]
        + seq_score * weights["sequence"]
        + graph_score * weights["graph"]
    )

    return min(combined, 1.0)
