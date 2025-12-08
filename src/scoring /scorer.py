# src/scoring/scorer.py
elif amt <= 100000:
return 0.5
else:
return 0.85


def score_pre_transaction(self, tx: dict, features: dict) -> dict:
# 1. Fast rule checks
rule_score, reasons = self.rules_check(tx, features)
# 2. Tabular model (dummy)
tab_score = self.dummy_tabular_score(features)
# 3. Graph/sequential placeholders
seq_score = 0.0
graph_score = 0.0
contract_score = 0.0


# Combine with weights
weights = {
'rules': 0.35,
'contract': 0.20,
'tabular': 0.25,
'sequence': 0.10,
'graph': 0.10
}
combined = (weights['rules']*rule_score + weights['contract']*contract_score +
weights['tabular']*tab_score + weights['sequence']*seq_score + weights['graph']*graph_score)
risk_score = min(100, round(combined * 100, 2))


# Label
if risk_score >= 85:
label = 'high_risk'
elif risk_score >= 60:
label = 'suspicious'
else:
label = 'safe'


# Build top features list (simple)
top_features = []
for r in reasons:
top_features.append({'feature': r, 'value': True, 'impact': 0.5})
if not top_features:
top_features.append({'feature': 'amount_usd', 'value': features.get('amount_usd', 0), 'impact': tab_score})


reason_text = ' ; '.join(reasons) if reasons else 'No immediate blacklists or contract red flags. Check amount and behavior.'


resp = {
'risk_score': risk_score,
'risk_label': label,
'component_scores': {
'tabular': round(tab_score,3),
'sequence': round(seq_score,3),
'graph': round(graph_score,3),
'contract': round(contract_score,3),
'rules': round(rule_score,3)
},
'top_features': top_features,
'reason_text': reason_text,
'action': 'block' if risk_score>=85 else ('warn' if risk_score>=60 else 'allow')
}
return resp
