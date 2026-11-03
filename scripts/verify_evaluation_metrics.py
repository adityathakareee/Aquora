import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, recall_score,
    f1_score, brier_score_loss, confusion_matrix, classification_report
)

df = pd.read_parquet('data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet')

CORE_11 = [
    'rainfall_1h_mm', 'rainfall_3h_mm', 'rainfall_6h_mm', 'rainfall_24h_mm', 'rainfall_72h_mm',
    'rainfall_anomaly_index', 'elevation_m', 'slope_deg', 'distance_to_river_m',
    'historical_flood_frequency', 'landcover_class'
]

# Strict anti-leakage: historical_flood_frequency excluded from model training
MODEL_FEATURES = [f for f in CORE_11 if f != 'historical_flood_frequency']

train = df[df['split'] == 'train']
val = df[df['split'] == 'validation']
test = df[df['split'] == 'test']

X_train, y_train = train[MODEL_FEATURES], train['flood_label'].astype(int).values
X_val, y_val = val[MODEL_FEATURES], val['flood_label'].astype(int).values
X_test, y_test = test[MODEL_FEATURES], test['flood_label'].astype(int).values

n_test = len(y_test)
n_pos = int((y_test == 1).sum())
n_neg = int((y_test == 0).sum())

print('=' * 80)
print('EVALUATION VERIFICATION ON NATURAL HELD-OUT TEST EVENT (DFO 2507)')
print(f'Total Test Samples: {n_test:,d} | Positive: {n_pos:,d} (5.819%) | Negative: {n_neg:,d} (94.181%)')
print('=' * 80)

# Baseline 1: Constant Training Prior (P = 0.5000)
p_train = float(y_train.mean()) # 0.50
prior_probs = np.full(n_test, p_train)
prior_brier = brier_score_loss(y_test, prior_probs)
prior_preds = (prior_probs >= 0.5).astype(int) # All 1s
cm_prior = confusion_matrix(y_test, prior_preds)
tn_p, fp_p, fn_p, tp_p = cm_prior.ravel()
assert tn_p + fp_p + fn_p + tp_p == n_test
assert tp_p + fn_p == n_pos
assert tn_p + fp_p == n_neg

print('\n--- BASELINE 1: Constant Training Prior (P = 0.50) ---')
print(f'Brier Score:   {prior_brier:.4f}')
print(f'Precision:     {tp_p / (tp_p + fp_p):.4f}')
print(f'Recall:        {tp_p / (tp_p + fn_p):.4f}')
print(f'F1-Score:      {2*tp_p / (2*tp_p + fp_p + fn_p):.4f}')
print(f'FPR:           {fp_p / (fp_p + tn_p):.4f} (FP: {fp_p:,d}, TN: {tn_p:,d})')
print(f'FNR:           {fn_p / (fn_p + tp_p):.4f} (FN: {fn_p:,d}, TP: {tp_p:,d})')
print(f'Confusion Matrix:\n{cm_prior}')

# Baseline 2: Physical Elevation Inverted Ranking & Validation-Selected Threshold
elev_min = float(X_train['elevation_m'].min())
elev_max = float(X_train['elevation_m'].max())
elev_score_val = 1.0 - (X_val['elevation_m'].clip(elev_min, elev_max) - elev_min) / (elev_max - elev_min + 1e-5)
elev_score_test = 1.0 - (X_test['elevation_m'].clip(elev_min, elev_max) - elev_min) / (elev_max - elev_min + 1e-5)

# Ranking metrics (threshold-independent; monotonic with lower elevation)
elev_roc = roc_auc_score(y_test, elev_score_test)
elev_pr = average_precision_score(y_test, elev_score_test)

# Select threshold strictly on validation set (NEVER test set):
best_th_elev = 0.5
best_f1_elev = 0
for th in np.linspace(0.01, 0.99, 100):
    f1_cand = f1_score(y_val, (elev_score_val >= th).astype(int), zero_division=0)
    if f1_cand > best_f1_elev:
        best_f1_elev = f1_cand
        best_th_elev = th

elev_preds_test = (elev_score_test >= best_th_elev).astype(int)
cm_elev = confusion_matrix(y_test, elev_preds_test)
tn_e, fp_e, fn_e, tp_e = cm_elev.ravel()
assert tn_e + fp_e + fn_e + tp_e == n_test
assert tp_e + fn_e == n_pos
assert tn_e + fp_e == n_neg

print('\n--- BASELINE 2: Elevation Heuristic ---')
print(f'Ranking Metrics (Ordinal Inverted Elevation):')
print(f'  ROC-AUC:       {elev_roc:.4f}')
print(f'  PR-AUC:        {elev_pr:.4f}')
print(f'  Brier Score:   N/A (Raw inverted elevation is an ordinal ranking score, not a calibrated probability estimate)')
print(f'Classification Metrics (Validation-Tuned Threshold = {best_th_elev:.4f}; Validation F1 = {best_f1_elev:.4f}):')
print(f'  Precision:     {tp_e / (tp_e + fp_e):.4f}')
print(f'  Recall:        {tp_e / (tp_e + fn_e):.4f}')
print(f'  F1-Score:      {2*tp_e / (2*tp_e + fp_e + fn_e):.4f}')
print(f'  FPR:           {fp_e / (fp_e + tn_e):.4f} (FP: {fp_e:,d}, TN: {tn_e:,d})')
print(f'  FNR:           {fn_e / (fn_e + tp_e):.4f} (FN: {fn_e:,d}, TP: {tp_e:,d})')
print(f'Confusion Matrix:\n{cm_elev}')

# Primary Model: XGBoost Classifier
clf = xgb.XGBClassifier(
    n_estimators=150, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42,
    eval_metric='logloss', missing=np.nan
)
clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

val_probs = clf.predict_proba(X_val)[:, 1]
best_th_xgb = 0.5
best_f1_xgb = 0
for th in np.linspace(0.05, 0.95, 91):
    f1_cand = f1_score(y_val, (val_probs >= th).astype(int), zero_division=0)
    if f1_cand > best_f1_xgb:
        best_f1_xgb = f1_cand
        best_th_xgb = th

test_probs = clf.predict_proba(X_test)[:, 1]
test_roc = roc_auc_score(y_test, test_probs)
test_pr = average_precision_score(y_test, test_probs)
test_brier = brier_score_loss(y_test, test_probs)

for name, th in [('Default Threshold (0.50)', 0.50), (f'Validation-Selected Threshold ({best_th_xgb:.2f})', best_th_xgb)]:
    preds = (test_probs >= th).astype(int)
    cm = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel()
    assert tn + fp + fn + tp == n_test
    assert tp + fn == n_pos
    assert tn + fp == n_neg
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn)
    fnr = fn / (fn + tp)
    print(f'\n--- PRIMARY MODEL (XGBoost) at {name} ---')
    print(f'ROC-AUC:       {test_roc:.4f}')
    print(f'PR-AUC:        {test_pr:.4f}')
    print(f'Brier Score:   {test_brier:.4f}')
    print(f'Precision:     {prec:.4f}')
    print(f'Recall:        {rec:.4f}')
    print(f'F1-Score:      {f1:.4f}')
    print(f'FPR:           {fpr:.4f} (FP: {fp:,d}, TN: {tn:,d})')
    print(f'FNR:           {fnr:.4f} (FN: {fn:,d}, TP: {tp:,d})')
    print(f'Confusion Matrix:\n{cm}')
