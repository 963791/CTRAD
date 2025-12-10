# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
# Local imports — adapt if your modules live under src/
try:
    from src.features.feature_builder import FeatureBuilder
    from src.scoring.scorer import Scorer
except Exception:
    # fallback if you don't have src/ structure
    FeatureBuilder = None
    Scorer = None

st.set_page_config(page_title='CTRAD — Pre-Transaction Risk Checker', layout='wide')

st.title('CTRAD — Pre-Transaction Risk & Anomaly Detection (Pre-transaction)')
st.write('Check a transaction for risk BEFORE you send it. This is a prototype UI — models are pluggable.')

# Sidebar: inputs (must be indented inside the with block)
with st.sidebar:
    st.header('Inputs')
    chain = st.selectbox('Chain', ['ethereum', 'bsc', 'polygon'], index=0)
    from_addr = st.text_input('Sender Address (from_addr)', value='0xSender...')
    to_addr = st.text_input('Recipient Address (to_addr)', value='0xRecipient...')
    token_symbol = st.text_input('Token Symbol', value='ETH')
    token_contract = st.text_input('Token Contract (optional)', value='')
    amount = st.number_input('Amount (in token units)', value=0.5, format='%f')
    amount_usd = st.number_input('Amount (USD)', value=800.0, format='%f')
    gas_price = st.number_input('Gas Price (Gwei)', value=50.0)
    check_button = st.button('Check Risk Before Sending')
    st.markdown('---')
    st.write('Tip: Use the sample data or connect an API later.')

# Two columns for summary and model info
col1, col2 = st.columns([2, 3])

with col1:
    st.subheader('Quick Info')
    st.write('Timestamp:', datetime.utcnow().isoformat() + 'Z')
    st.write('From:', from_addr)
    st.write('To:', to_addr)
    st.write('Token:', token_symbol)
    st.write('Amount (USD):', amount_usd)

with col2:
    st.subheader('Model & Settings')
    st.write('Model: CTRAD - Ensemble Prototype')
    st.write('Mode: Pre-transaction (fast checks + cached features)')

# Initialize feature builder and scorer if available; else use simple fallback
if FeatureBuilder is not None:
    fb = FeatureBuilder()
else:
    fb = None

if Scorer is not None:
    scorer = Scorer(model_dir='models')
else:
    scorer = None

if check_button:
    with st.spinner('Scoring transaction...'):
        tx = {
            'chain': chain,
            'from_addr': from_addr,
            'to_addr': to_addr,
            'token_symbol': token_symbol,
            'token_contract': token_contract,
            'amount': amount,
            'amount_usd': amount_usd,
            'gas_price': gas_price,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        # Build features (fallback minimal)
        if fb is not None and hasattr(fb, 'transform_one'):
            features = fb.transform_one(tx)
        else:
            features = {
                'amount_usd': amount_usd,
                'to_age_days': 120,
                'is_contract_to': bool(token_contract)
            }

        # Score (fallback simple logic)
        if scorer is not None and hasattr(scorer, 'score_pre_transaction'):
            score_res = scorer.score_pre_transaction(tx, features)
        else:
            # Simple fallback scoring
            amt = features.get('amount_usd', 0)
            if amt > 100000:
                risk_score = 90
                label = 'high_risk'
            elif amt > 10000:
                risk_score = 65
                label = 'suspicious'
            else:
                risk_score = 10
                label = 'safe'
            score_res = {
                'risk_score': risk_score,
                'risk_label': label,
                'component_scores': {'tabular': 0.5},
                'top_features': [{'feature': 'amount_usd', 'value': amt, 'impact': 0.5}],
                'reason_text': 'Fallback heuristic: large amount' if amt > 10000 else 'Fallback heuristic: amount OK',
                'action': 'block' if risk_score >= 85 else ('warn' if risk_score >= 60 else 'allow')
            }

    # Display results
    st.metric('Risk Score', f"{score_res['risk_score']} / 100")
    if score_res['risk_score'] >= 85:
        st.error(f"{score_res['risk_label'].upper()} — {score_res['reason_text']}")
    elif score_res['risk_score'] >= 60:
        st.warning(f"{score_res['risk_label'].upper()} — {score_res['reason_text']}")
    else:
        st.success(f"{score_res['risk_label'].upper()} — {score_res['reason_text']}")

    st.subheader('Component Scores')
    st.json(score_res.get('component_scores', {}))

    st.subheader('Top Features / Reasons')
    st.json(score_res.get('top_features', []))

    with st.expander('Full JSON response'):
        st.json(score_res)

st.markdown('---')
st.caption('CTRAD prototype — replace dummy models in src/scoring/scorer.py with your trained models and update FeatureBuilder to fetch real features.')
