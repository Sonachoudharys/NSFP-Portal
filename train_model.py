"""
============================================================
NATIONAL SCHEME FRAUD PORTAL — NSFP v2.0
train_model.py | Developed by Sona Choudhary | 2026
AI Model Training Script — IsolationForest
============================================================
"""

import os
import logging
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score, precision_score,
    recall_score, f1_score, confusion_matrix
)
import joblib

# ─── LOGGING ────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NSFP-Train")

# ─── PATHS ───────────────────────────────────────────────────
DATA_PATH  = "fraud_output.csv"
MODEL_PATH = "fraud_model.pkl"
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

# ─── LOAD DATA ───────────────────────────────────────────────
logger.info(f"Loading dataset from '{DATA_PATH}'...")
df = pd.read_csv(DATA_PATH)
df.columns = df.columns.str.lower().str.strip()
logger.info(f"Dataset shape: {df.shape}")
logger.info(f"Columns: {list(df.columns)}")
logger.info(f"Class distribution:\n{df['fraud_predicted'].value_counts()}")

# ─── FEATURES & LABELS ───────────────────────────────────────
FEATURES = ["age", "income", "schemes_taken"]
LABEL    = "fraud_predicted"

X = df[FEATURES]
y = df[LABEL]

# ─── TRAIN / TEST SPLIT ──────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")

# ─── TRAIN MODEL ─────────────────────────────────────────────
logger.info("Training IsolationForest...")
model = IsolationForest(
    n_estimators=200,
    contamination=0.2,
    max_samples="auto",
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train)

# ─── PREDICT & MAP LABELS ────────────────────────────────────
raw_preds = model.predict(X_test)
# IsolationForest: -1 = anomaly (fraud), 1 = normal
preds = [1 if p == -1 else 0 for p in raw_preds]

# ─── METRICS ─────────────────────────────────────────────────
acc  = accuracy_score(y_test, preds)
prec = precision_score(y_test, preds, zero_division=0)
rec  = recall_score(y_test, preds, zero_division=0)
f1   = f1_score(y_test, preds, zero_division=0)

logger.info("=" * 40)
logger.info(f"  Accuracy  : {acc:.4f} ({acc*100:.2f}%)")
logger.info(f"  Precision : {prec:.4f}")
logger.info(f"  Recall    : {rec:.4f}")
logger.info(f"  F1 Score  : {f1:.4f}")
logger.info("=" * 40)

# ─── SAVE MODEL ──────────────────────────────────────────────
joblib.dump(model, MODEL_PATH)
logger.info(f"Model saved → {MODEL_PATH}")

# ─── CONFUSION MATRIX PLOT ───────────────────────────────────
cm = confusion_matrix(y_test, preds)

fig, ax = plt.subplots(figsize=(6, 5))
fig.patch.set_facecolor("#0b1528")
ax.set_facecolor("#0b1528")

sns.heatmap(
    cm, annot=True, fmt="d", cmap="YlOrRd",
    xticklabels=["Genuine", "Fraud"],
    yticklabels=["Genuine", "Fraud"],
    linewidths=0.5, linecolor="#1e3a5f",
    ax=ax, cbar_kws={"shrink": 0.8}
)

ax.set_title("Confusion Matrix — IsolationForest", color="#FFD700", fontsize=13, pad=14)
ax.set_xlabel("Predicted Label", color="#aabbcc", fontsize=10)
ax.set_ylabel("True Label",      color="#aabbcc", fontsize=10)
ax.tick_params(colors="#aabbcc")

plt.tight_layout()
plt.savefig(os.path.join(STATIC_DIR, "confusion_matrix.png"), dpi=150, bbox_inches="tight")
plt.close()
logger.info("Confusion matrix saved.")

# ─── ACCURACY CHART ──────────────────────────────────────────
metrics = {"Accuracy": acc, "Precision": prec, "Recall": rec, "F1 Score": f1}
colors  = ["#3b82f6", "#22c55e", "#f97316", "#FFD700"]

fig2, ax2 = plt.subplots(figsize=(7, 4))
fig2.patch.set_facecolor("#0b1528")
ax2.set_facecolor("#0b1528")

bars = ax2.bar(metrics.keys(), metrics.values(), color=colors, width=0.5, zorder=3)
ax2.set_ylim(0, 1.1)
ax2.set_ylabel("Score", color="#aabbcc", fontsize=10)
ax2.set_title("Model Evaluation Metrics", color="#FFD700", fontsize=13, pad=14)
ax2.tick_params(colors="#aabbcc")
ax2.grid(axis="y", color="rgba(255,255,255,0.05)", zorder=0)
ax2.set_facecolor("#0b1528")

for bar, val in zip(bars, metrics.values()):
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.02,
        f"{val:.2%}",
        ha="center", va="bottom",
        color="white", fontsize=9, fontweight="bold"
    )

for spine in ax2.spines.values():
    spine.set_edgecolor("#1e3a5f")

plt.tight_layout()
plt.savefig(os.path.join(STATIC_DIR, "accuracy_chart.png"), dpi=150, bbox_inches="tight")
plt.close()
logger.info("Accuracy chart saved.")

logger.info("✅ Training complete. All artifacts saved.")
print("\n✅ NSFP Model Training Complete!")
print(f"   Accuracy : {acc*100:.2f}%")
print(f"   F1 Score : {f1:.4f}")
print(f"   Model    : {MODEL_PATH}")
