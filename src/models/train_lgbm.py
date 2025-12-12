# src/models/train_lgbm.py
"""
Train a LightGBM classifier for pre-transaction risk.
- Uses FeatureBuilder to create features (expects src/features/feature_builder.py)
- Uses rule-based pseudo-labeling if no ground-truth label column present.
- Saves model to models/model_lgbm_v1.pkl and pipeline to models/feature_builder_v1.pkl
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
from sklearn.metrics import precision_score, recall_score
from datetime import datetime

# Replace import path if your FeatureBuilder lives elsewhere
try:
    from src.features.feature_builder import FeatureBuilder
except Exception:
    # minimal fallback FeatureBuilder
    class FeatureBuilder:
        def fit(self, df): return self
        def transform(self, df):
            df2 = df.copy()
            df2['log_amount'] = np.log1p(df2.get('amount_usd', 0.0).astype(float))
            df2['to_is_contract'] = df2['token_contract'].notnull().astype(int) if 'token_contract' in df2.columns else 0
            return df2
        def fit_transform(self, df):
            self.fit(df)
            return self.transform(df)

# Helper: pseudo-labeling using simple rules (fast way to produce training labels)
def pseudo_label(df: pd.DataFrame) -> pd.Series:
    # label=1 (risky) if any of these simple conditions hold
    conds = []
    conds.append(df['amount_usd'] >= 100000)   # very large
    conds.append(df['amount_usd'] >= 10000)    # large
    if 'to_addr' in df.columns:
        blacklist = {'0xscamdead00000000000000000000000000000000', '0xphishdead000000000000000000000000000000'}
        conds.append(df['to_addr'].str.lower().isin(blacklist))
    # combine
    combined = np.logical_or.reduce(conds)
    return combined.astype(int)

def precision_at_k(y_true, scores, k=100):
    # compute precision in top-k scoring examples
    idx = np.argsort(scores)[-k:][::-1]
    return precision_score(y_true[idx], (scores[idx] >= 0.5).astype(int))

def train():
    os.makedirs('models', exist_ok=True)
    # load data
    if os.path.exists('data/sample_transactions.csv'):
        df = pd.read_csv('data/sample_transactions.csv', parse_dates=['timestamp'], keep_default_na=False)
    else:
        raise FileNotFoundError("data/sample_transactions.csv not found. Create sample data first.")

    # ensure numeric column
    if 'amount_usd' not in df.columns:
        raise ValueError("CSV must contain 'amount_usd' column")

    # create labels: use 'label' if exists otherwise pseudo-label
    if 'label' in df.columns and df['label'].notna().any():
        y = (df['label'] != 'normal').astype(int)
    else:
        y = pseudo_label(df)

    # feature building
    fb = FeatureBuilder()
    try:
        X = fb.fit_transform(df)
    except Exception:
        X = fb.fit(df).transform(df)

    # decide features to use (auto-detect numeric columns)
    # exclude identifiers
    drop_cols = ['tx_id', 'timestamp', 'from_addr', 'to_addr', 'token_symbol', 'token_contract', 'label']
    features = [c for c in X.columns if c not in drop_cols and np.issubdtype(X[c].dtype, np.number)]
    if not features:
        # fallback: use amount_usd only
        X['amount_usd'] = df['amount_usd'].astype(float)
        features = ['amount_usd']

    Xf = X[features].fillna(0.0)

    # train/test split by time if timestamp exists (simulate production)
    if 'timestamp' in df.columns:
        df['ts_sort'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('ts_sort')
        Xf = Xf.loc[df.index]
        y = pd.Series(y).loc[df.index].values

    X_train, X_test, y_train, y_test = train_test_split(Xf, y, test_size=0.2, random_state=42, shuffle=True)

    lgb_train = lgb.Dataset(X_train, label=y_train)
    lgb_eval = lgb.Dataset(X_test, label=y_test, reference=lgb_train)

    params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'verbosity': -1,
        'learning_rate': 0.05,
        'num_leaves': 31,
        'seed': 42,
    }

    gbm = lgb.train(params, lgb_train, num_boost_round=500, valid_sets=[lgb_train, lgb_eval],
                    early_stopping_rounds=30, verbose_eval=False)

    # predict probs
    yprob = gbm.predict(X_test, num_iteration=gbm.best_iteration)
    try:
        roc = roc_auc_score(y_test, yprob)
    except Exception:
        roc = float('nan')
    precision, recall, _ = precision_recall_curve(y_test, yprob)
    pr_auc = auc(recall, precision)

    # Precision@K
    k = min(100, len(y_test))
    prec_at_k = precision_at_k(y_test, yprob, k=k)

    # Save model and feature builder
    joblib.dump(gbm, 'models/model_lgbm_v1.pkl')
    joblib.dump(fb, 'models/feature_builder_v1.pkl')

    # Save a small report
    report = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'features_used': features,
        'roc_auc': float(roc),
        'pr_auc': float(pr_auc),
        'precision_at_{}'.format(k): float(prec_at_k),
        'n_train': len(X_train),
        'n_test': len(X_test),
        'model_file': 'models/model_lgbm_v1.pkl'
    }
    pd.Series(report).to_json('models/train_report.json')

    print("Training complete. Metrics:", report)
    print("Model saved to models/model_lgbm_v1.pkl")
    return gbm, fb, report

if __name__ == "__main__":
    train()
