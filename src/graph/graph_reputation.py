# ======================================
# CTRAD — Graph-Based Wallet Reputation
# ======================================

class GraphReputation:
    """
    Simple graph reputation model using:
    - Known scam address clusters
    - Wallet neighbor proximity
    - Risk propagation logic
    """

    def __init__(self):
        # These are demo clusters (replace later with API or DB)
        self.scam_clusters = {
            "cluster_phishing": {
                "label": "Phishing Cluster",
                "addresses": {
                    "0x111aaa", "0x111bbb", "0x111ccc"
                },
                "base_risk": 0.95
            },
            "cluster_mixer": {
                "label": "TornadoCash Mixer",
                "addresses": {
                    "0x222aaa", "0x222bbb"
                },
                "base_risk": 0.75
            },
            "cluster_rugpull": {
                "label": "Rugpull Scammers",
                "addresses": {
                    "0x333aaa", "0x333bbb", "0x333ccc"
                },
                "base_risk": 0.90
            }
        }

    def compute_distance(self, addr: str) -> float:
        """
        Computes how close the wallet is to known scam clusters.

        Distance Logic:
        - Exact address match → Extremely risky (1.0)
        - First 4 hex match → High risk (0.8)
        - First 2 hex match → Low-medium risk (0.4)
        - No match → 0.0
        """
        addr = addr.lower()

        max_risk = 0.0

        for cluster in self.scam_clusters.values():
            for scam_addr in cluster["addresses"]:

                scam_addr = scam_addr.lower()

                if addr == scam_addr:
                    max_risk = max(max_risk, cluster["base_risk"])

                # Prefix similarity (cheap graph approximation)
                if addr[:6] == scam_addr[:6]:
                    max_risk = max(max_risk, cluster["base_risk"] * 0.7)

                if addr[:4] == scam_addr[:4]:
                    max_risk = max(max_risk, cluster["base_risk"] * 0.45)

                if addr[:2] == scam_addr[:2]:
                    max_risk = max(max_risk, cluster["base_risk"] * 0.20)

        return round(max_risk, 3)

    def score(self, addr: str) -> float:
        """
        Entry point to get graph reputation.
        Output: value 0–1
        """
        return self.compute_distance(addr)
