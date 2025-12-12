class SequenceModel:
    """
    Lightweight mock of a sequence anomaly model.
    Later you can replace this with a real LSTM model.
    """

    def __init__(self):
        pass

    def predict(self, history_amounts, current_amount):
        """
        history_amounts: list of past USD amounts for this sender
        current_amount: float
        returns: risk_score (0 to 1)
        """

        # No history → can't compare → mild neutral score
        if not history_amounts or len(history_amounts) < 3:
            return 0.10  # small risk

        avg = sum(history_amounts) / len(history_amounts)
        diffs = [(x - avg) ** 2 for x in history_amounts]
        std = (sum(diffs) / len(history_amounts)) ** 0.5

        # If std is extremely small, avoid divide by zero
        if std < 1e-6:
            std = 1e-6

        # z-score
        z = abs(current_amount - avg) / std

        # map z-score → risk (0–1)
        risk = min(z / 5, 1.0)

        return risk
