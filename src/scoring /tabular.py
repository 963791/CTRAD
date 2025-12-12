import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler


class TabularModel:
    """
    Lightweight RandomForest model for CTRAD.
    Trains on synthetic labeled data if no model file exists.
    """

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=40,
            max_depth=5,
            random_state=42
        )
        self.scaler = MinMaxScaler()

        # Train immediately
        self._train_model()

    def _train_model(self):
        """
        Train a basic, small ML model for scoring.
        Features:
        - amount_usd
        - token volatility score (synthetic)
        - suspicious address flag
        """

        np.random.seed(42)

        # Synthetic dataset of 400 rows
        data = {
            "amount_usd": np.random.uniform(1, 5000, 400),
            "token_volatility": np.random.uniform(0, 1, 400),
            "addr_flag": np.random.choice([0, 1], 400, p=[0.85, 0.15]),
        }

        df = pd.DataFrame(data)

        # Labeling rule
        df["label"] = (
            (df["amount_usd"] > 2000).astype(int) |
            (df["token_volatility"] > 0.7).astype(int) |
            (df["addr_flag"] == 1).astype(int)
        )

        X = df[["amount_usd", "token_volatility", "addr_flag"]]
        y = df["label"]

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict(self, amount_usd: float, token_symbol: str, from_addr: str):
        """
        Return risk probability (0–1).
        """

        # Token volatility stub (upgrade later)
        token_volatility = {
            "ETH": 0.2,
            "USDT": 0.05,
            "USDC": 0.05,
            "BNB": 0.18,
            "DOGE": 0.45,
            "SHIB": 0.55,
        }.get(token_symbol.upper(), 0.30)

        # Address pattern flag
        addr_flag = 1 if from_addr.lower().startswith("0xabc") else 0

        X = np.array([[amount_usd, token_volatility, addr_flag]])
        X_scaled = self.scaler.transform(X)

        prob = self.model.predict_proba(X_scaled)[0][1]
        return float(prob)
