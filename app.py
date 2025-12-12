import streamlit as st
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="CTRAD – Pre-Transaction Risk Engine", layout="wide")

st.title("🔐 CTRAD — Pre-Transaction Risk & Anomaly Detection")
st.write("Check a transaction for risk **BEFORE** sending it.")

st.markdown("---")

# ------------------------------
# SECTION 1 — INPUT FORM
# ------------------------------
st.header("Input Transaction Details")

col1, col2 = st.columns(2)

with col1:
    from_addr = st.text_input("Sender Wallet", "0xSender...")
    to_addr = st.text_input("Recipient Wallet", "0xRecipient...")
    token_symbol = st.text_input("Token Symbol", "ETH")
    amount_usd = st.number_input("Amount (USD)", value=800.0)

with col2:
    st.subheader("Quick Info")
    st.write("Timestamp:", datetime.utcnow().isoformat() + "Z")

    st.subheader("Model & Settings")
    st.write("Model: CTRAD - Ensemble Prototype")
    st.write("Mode: Pre-transaction risk scoring")

st.markdown("---")

# ======================================================
# SECTION 2 — SCORER PLACEHOLDER (Replace with real model)
# ======================================================

# Since no real model yet → Fake but realistic output
def fake_scorer():
    return {
        "risk_score": 25,   # 0–100
        "risk_label": "safe",
        "component_scores": {
            "rules": 0.0,
            "tabular": 0.1,
            "sequence": 0.0,
            "graph": 0.0,
            "contract": 0.0
        },
        "top_features": [
            {"feature": "amount_usd", "value": amount_usd, "impact": 0.1}
        ],
        "reason_text": "Amount is normal. No high-risk patterns detected.",
        "action": "allow"
    }

# Run scoring when button is clicked
if st.button("Run Risk Analysis"):
    score_res = fake_scorer()
else:
    score_res = None

# ------------------------------
# SECTION 3 — RISK METER
# ------------------------------

# ======== GAUGE HELPER ==========
def render_plotly_gauge(score: float):
    try:
        import plotly.graph_objects as go
    except:
        return None

    value = max(0, min(100, float(score)))

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': " /100", 'font': {'size': 28}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {"range": [0, 30], "color": "#2ecc71"},
                {"range": [30, 60], "color": "#f1c40f"},
                {"range": [60, 100], "color": "#e74c3c"},
            ],
        }
    ))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def render_risk_meter(score: float):
    fig = render_plotly_gauge(score)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.progress(int(score))

# ======== ACTION BADGE ==========
def action_from_score(score: float):
    if score >= 85:
        return ("BLOCK", "❌", "#ff4b4b")
    elif score >= 60:
        return ("WARN", "⚠️", "#f1c40f")
    else:
        return ("ALLOW", "✅", "#2ecc71")

# ======== COMPONENT CARDS ==========
def render_component_cards(component_scores: dict):
    cols = st.columns(len(component_scores))
    for (name, val), col in zip(component_scores.items(), cols):
        pct = int(val * 100)
        with col:
            st.metric(name.capitalize(), f"{pct}%")

# ------------------------------
# SECTION 4 — SHOW RESULTS
# ------------------------------

if score_res:

    st.markdown("---")
    st.header("🔍 Risk Analysis Result")

    label = score_res.get("risk_label", "").upper()
    risk_score = score_res.get("risk_score", 0)
    comp_scores = score_res.get("component_scores", {})
    top_features = score_res.get("top_features", [])
    reason_text = score_res.get("reason_text", "")

    st.write(f"**Label:** {label}")

    render_risk_meter(risk_score)

    # Action
    action_text, action_icon, action_color = action_from_score(risk_score)
    st.markdown(
        f"""
        <div style='background:{action_color};color:white;padding:12px;border-radius:8px;
        width:160px;font-weight:bold;text-align:center'>
        {action_icon} {action_text}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write(f"**Reason:** {reason_text}")

    # Component Scores
    st.subheader("Component Scores")
    render_component_cards(comp_scores)

    # Top Features
    st.subheader("Top Contributing Features")
    if top_features:
        try:
            df = pd.DataFrame(top_features)
            st.table(df)
        except:
            st.write(top_features)
    else:
        st.write("No feature explanations available.")

    # History placeholder
    st.subheader("Recent Flags / History")
    st.write("History will appear here once DB/Cache is connected.")

    # JSON
    with st.expander("Full Scoring JSON"):
        st.json(score_res)
