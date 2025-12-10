# === Advanced Risk Meter UI (drop into app.py after scoring) ===
import streamlit as st
from datetime import datetime
import pandas as pd

# Plotly gauge helper (optional)
def render_plotly_gauge(score: float):
    try:
        import plotly.graph_objects as go
    except Exception:
        return None  # caller will fallback to st.progress

    # Bound score
    val = max(0, min(100, float(score)))

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={'suffix': " /100", 'font': {'size': 30}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': "darkblue", 'thickness': 0.25},
            'bgcolor': "white",
            'steps': [
                {'range': [0, 30], 'color': "#2ecc71"},    # green
                {'range': [30, 60], 'color': "#f1c40f"},   # yellow
                {'range': [60, 100], 'color': "#e74c3c"}   # red
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': val
            }
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350)
    return fig

def render_risk_meter(score: float):
    """Render gauge or fallback progress bar and return action color/text."""
    fig = render_plotly_gauge(score)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        # fallback
        st.progress(int(max(0, min(100, score))))
        st.write(f"Risk Score: **{score} / 100**")

# Present compact component cards
def render_component_cards(component_scores: dict):
    cols = st.columns(len(component_scores))
    for (k, v), col in zip(component_scores.items(), cols):
        with col:
            v_pct = int(round(v * 100)) if (0 <= v <= 1) else int(v if v <= 100 else min(100, v))
            st.metric(label=k.capitalize(), value=f"{v_pct}%", delta=None)

# Suggested action mapping
def action_from_score(score: float):
    if score >= 85:
        return ("BLOCK", "❌", "#ff4b4b")
    elif score >= 60:
        return ("WARN", "⚠️", "#f1c40f")
    else:
        return ("ALLOW", "✅", "#2ecc71")

# --- Main results rendering (use the scorer output) ---
# Example: score_res = scorer.score_pre_transaction(tx, features)
# Make sure `score_res` has keys: risk_score, risk_label, component_scores, top_features, reason_text, action

if 'score_res' in globals():
    result = score_res
else:
    # Defensive fallback: if variable isn't present, create a dummy safe result
    result = {
        'risk_score': 10,
        'risk_label': 'safe',
        'component_scores': {'rules': 0.0, 'tabular': 0.1, 'sequence': 0.0, 'graph': 0.0, 'contract': 0.0},
        'top_features': [{'feature': 'amount_usd', 'value': 800.0, 'impact': 0.1}],
        'reason_text': 'Fallback: no scorer available.',
        'action': 'allow'
    }

risk_score = result.get('risk_score', 0)
component_scores = result.get('component_scores', {})
top_features = result.get('top_features', [])
reason_text = result.get('reason_text', '')
label = result.get('risk_label', '').upper()

st.markdown("---")
st.header("🔍 Risk Analysis Result")
st.write(f"**Label:** {label}")

# Gauge / Progress
render_risk_meter(risk_score)

# Suggested action badge
action_text, action_icon, action_color = action_from_score(risk_score)
badge_col1, badge_col2 = st.columns([1, 4])
with badge_col1:
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;justify-content:center'>
            <div style='background:{action_color};color:white;padding:10px 16px;border-radius:8px;font-weight:700'>
                {action_icon} {action_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with badge_col2:
    st.write(f"**Reason:** {reason_text}")

# Component mini-cards
st.subheader("Component Scores")
render_component_cards(component_scores)

# Top features & explanation
st.subheader("Top Contributing Features")
if isinstance(top_features, list) and top_features:
    # show as dataframe for clarity
    try:
        df_feats = pd.DataFrame(top_features)
        # ensure columns presence
        if 'impact' not in df_feats.columns:
            df_feats['impact'] = df_feats.get('impact', 0)
        st.table(df_feats)
    except Exception:
        # fallback rendering
        for f in top_features:
            st.write(f"- {f}")
else:
    st.write("No top features available.")

# Compact timeline or sparkline (optional placeholder)
st.subheader("Recent Flags / History")
st.write("Recent flagged events and history will be shown here. (Connect to DB or history cache.)")

# Expand for full JSON
with st.expander("Full scoring JSON"):
    st.json(result)
