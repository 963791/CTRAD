# app.py
import streamlit as st
import pandas as pd
from src.features.feature_builder import FeatureBuilder
from src.scoring.scorer import Scorer
from datetime import datetime


st.set_page_config(page_title='CTRAD — Pre-Transaction Risk Checker', layout='wide')


st.title('CTRAD — Pre-Transaction Risk & Anomaly Detection (Pre-transaction)')
st.markdown('Check a transaction for risk BEFORE you send it. This is a prototype UI — models are pluggable.')


with st.sidebar:
st.header('Inputs')
chain = st.selectbox('Chain', ['ethereum','bsc','polygon'], index=0)
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


# Initialize feature builder and scorer
fb = FeatureBuilder()
scorer = Scorer(model_dir='models') # models/ can contain your pickles/weights


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
st.caption('CTRAD prototype — replace dummy models in src/scoring/scorer.py with your trained models. Use feature builder in src/features to ensure consistent features.')
