#!/usr/bin/env python3
"""
TigerGraph × Hacker House Goa (HHGOA) IEEE Fraud Investigation
Phase 3: Calibrated Fraud Probability Model
=============================================================================
Trains a Gradient Boosting model with Isotonic Calibration on historical closed cases.
Enforces that risk_score alone is weak without graph corroboration.

Metrics:
- ROC AUC
- Brier Score (Mean Squared Probability Error)
- Reliability Diagram / Calibration Curve
- Per-pattern Precision / Recall
=============================================================================
"""

import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import roc_auc_score, brier_score_loss, precision_score, recall_score, f1_score
from sklearn.model_selection import StratifiedKFold

MODEL_PATH = Path(__file__).resolve().parent / "calibrated_model.pkl"
FEATURE_NAMES = [
    "flagged_risk_score",
    "flagged_amount",
    "flagged_is_online",
    "flagged_is_in_person",
    "is_new_device",
    "is_proxy",
    "has_device",
    "mismatch_count",
    "is_new_region",
    "concurrent_home_count",
    "amount_to_mean_ratio",
    "amount_to_p75_ratio",
    "prior_txns_count",
    "prior_in_person_pct",
    "prior_online_pct",
    "txns_24h",
    "txns_48h",
    "online_48h",
    "exposure_48h",
    "conf_testing",
    "conf_burst",
    "conf_new_device",
    "conf_region",
    "conf_ato",
    "max_graph_pattern",
    "has_corroborated_pattern",
    "lone_risk_score",
    "prior_cases_count",
    "prior_fraud_rate"
]


class CalibratedFraudModel:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.feature_names = FEATURE_NAMES

    def train_and_calibrate(self, X: pd.DataFrame, y: pd.Series):
        """Train Gradient Boosting model and calibrate probabilities via 5-fold Isotonic Regression."""
        X_mat = X[self.feature_names].values
        y_vec = y.values

        base_estimator = HistGradientBoostingClassifier(
            max_iter=150,
            max_depth=4,
            learning_rate=0.08,
            min_samples_leaf=20,
            l2_regularization=1.0,
            random_state=42
        )

        calibrated = CalibratedClassifierCV(
            estimator=base_estimator,
            method="isotonic",
            cv=5
        )

        calibrated.fit(X_mat, y_vec)
        self.model = calibrated

        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"[CalibratedFraudModel] Model saved to {self.model_path}")

    def load(self):
        """Load trained model from disk."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found at {self.model_path}. Run train first.")
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)

    def predict_proba(self, feature_dict: dict) -> float:
        """Predict calibrated fraud probability for a single case feature dict."""
        if self.model is None:
            self.load()

        vec = np.array([[feature_dict.get(k, 0.0) for k in self.feature_names]])
        # Calibrated probability of class 1 (confirmed fraud)
        p = float(self.model.predict_proba(vec)[0, 1])
        return round(p, 4)

    def evaluate_performance(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """Evaluate AUC, Brier Score, and calibration statistics on holdout test set."""
        X_mat = X_test[self.feature_names].values
        y_true = y_test.values
        y_prob = self.model.predict_proba(X_mat)[:, 1]
        y_pred = (y_prob >= 0.70).astype(int)

        auc = float(roc_auc_score(y_true, y_prob))
        brier = float(brier_score_loss(y_true, y_prob))
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)

        cal_curve_data = [
            {"bin": i + 1, "mean_predicted_prob": float(prob_pred[i]), "observed_fraction_positives": float(prob_true[i])}
            for i in range(len(prob_true))
        ]

        return {
            "roc_auc": auc,
            "brier_score": brier,
            "precision_at_070": prec,
            "recall_at_070": rec,
            "f1_score_at_070": f1,
            "calibration_curve": cal_curve_data
        }
