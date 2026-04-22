#!/usr/bin/env python3
"""
Hybrid Unseen Device Predictor - STABLE VERSION
No oscillation, rolling operator prior, multiplier smoothing
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

from dataclasses import dataclass
from typing import Dict, Any, List
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


@dataclass
class HybridConfig:
    model_dir: str = "hybrid_models"
    window_minutes: int = 5
    step_minutes: int = 2
    ewma_alpha: float = 0.35
    min_multiplier: float = 1.0
    max_multiplier: float = 2.2
    random_state: int = 42
    min_training_windows: int = 10


class HybridUnseenDevicePredictor:
    def __init__(self, cfg: HybridConfig = HybridConfig()):
        self.cfg = cfg
        os.makedirs(self.cfg.model_dir, exist_ok=True)

        self.multiplier_model = GradientBoostingRegressor(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=3,
            random_state=self.cfg.random_state
        )

        self.feature_columns = None
        self.last_estimate = None
        self.is_trained = False
        
        # STABILITY FIX 1: Multiplier smoothing state
        self.last_multiplier = 1.10
        self.last_cr_multiplier = 1.0
        
        # STABILITY FIX 2: Rolling operator prior (fixes Telenor bias)
        self.operator_prior = {}

    # ---------------------------
    # Helper: Smooth multiplier (prevents oscillation)
    # ---------------------------
    def _smooth_multiplier(self, m_new: float) -> float:
        """EWMA smoothing + step limiter (max 8% change per cycle)"""
        alpha = 0.20
        m = alpha * m_new + (1 - alpha) * self.last_multiplier

        # Step limiter: max +/- 8% per cycle
        upper = self.last_multiplier * 1.08
        lower = self.last_multiplier * 0.92
        m = min(max(m, lower), upper)

        # Hard bounds
        m = float(np.clip(m, self.cfg.min_multiplier, self.cfg.max_multiplier))
        self.last_multiplier = m
        return m

    # ---------------------------
    # Helper: Rolling operator prior (fixes bias)
    # ---------------------------
    def _update_operator_prior(self, df: pd.DataFrame):
        """EWMA rolling prior for operator distribution"""
        if "operator" not in df.columns:
            return
        
        op_counts = df.groupby("operator")["imsi"].nunique()
        if op_counts.sum() == 0:
            return
        
        current = (op_counts / op_counts.sum()).to_dict()
        
        # EWMA prior (beta = 0.15)
        beta = 0.15
        keys = set(self.operator_prior.keys()) | set(current.keys())
        
        for k in keys:
            old = self.operator_prior.get(k, 0.0)
            new = current.get(k, 0.0)
            self.operator_prior[k] = (1 - beta) * old + beta * new
        
        # Normalize
        s = sum(self.operator_prior.values())
        if s > 0:
            for k in self.operator_prior:
                self.operator_prior[k] /= s

    # ---------------------------
    # Capture-recapture baseline
    # ---------------------------
    @staticmethod
    def _chapman(n1: int, n2: int, m2: int) -> float:
        return ((n1 + 1) * (n2 + 1) / (m2 + 1)) - 1

    def _build_windows(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        x = df.copy()
        x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
        x = x.dropna(subset=["timestamp", "imsi"]).sort_values("timestamp")
        if x.empty:
            return []

        start = x["timestamp"].min().floor("min")
        end = x["timestamp"].max().ceil("min")
        win = pd.Timedelta(minutes=self.cfg.window_minutes)
        step = pd.Timedelta(minutes=self.cfg.step_minutes)

        windows = []
        t = start
        while t + win <= end + pd.Timedelta(seconds=1):
            w = x[(x["timestamp"] >= t) & (x["timestamp"] < t + win)]
            if len(w) > 5:
                windows.append(w)
            t += step
        return windows

    def capture_recapture_estimate(self, df: pd.DataFrame) -> Dict[str, Any]:
        observed = int(df["imsi"].nunique())
        windows = self._build_windows(df)
        
        if len(windows) < 2:
            return {
                "observed": observed,
                "cr_estimated_total": observed,
                "cr_multiplier": 1.0,
                "pairs": 0,
                "avg_overlap": 0.0
            }

        pair_N = []
        overlap_ratios = []
        
        for i in range(len(windows) - 1):
            a = set(windows[i]["imsi"].unique())
            b = set(windows[i + 1]["imsi"].unique())
            n1, n2, m2 = len(a), len(b), len(a.intersection(b))
            if n1 == 0 or n2 == 0:
                continue
            
            overlap_ratio = m2 / min(n1, n2) if min(n1, n2) > 0 else 0
            overlap_ratios.append(overlap_ratio)
            
            N = self._chapman(n1, n2, m2)
            N = max(N, max(n1, n2))
            pair_N.append(N)

        avg_overlap = float(np.mean(overlap_ratios)) if overlap_ratios else 0.0

        # Reliability gate
        if len(pair_N) < 4 or avg_overlap < 0.15:
            cr_multiplier = 1.0
            total = observed
        else:
            total = max(observed, int(round(np.median(pair_N))))
            cr_multiplier = float(np.clip(total / max(observed, 1), 
                                         self.cfg.min_multiplier, 
                                         self.cfg.max_multiplier))

        total = int(round(observed * cr_multiplier))

        return {
            "observed": observed,
            "cr_estimated_total": total,
            "cr_multiplier": cr_multiplier,
            "pairs": len(pair_N),
            "avg_overlap": avg_overlap
        }

    # ---------------------------
    # Feature engineering
    # ---------------------------
    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        x = df.copy()
        x["timestamp"] = pd.to_datetime(x["timestamp"], errors="coerce")
        x = x.dropna(subset=["timestamp", "imsi"])
        if x.empty:
            return pd.DataFrame()

        x["minute"] = x["timestamp"].dt.floor("min")
        g = x.groupby("minute", sort=True)

        rows = []
        for minute, grp in g:
            feat = {
                "hour": minute.hour,
                "minute_of_day": minute.hour * 60 + minute.minute,
                "day_of_week": minute.weekday(),
                "is_weekend": 1 if minute.weekday() >= 5 else 0,
                "observed_unique": grp["imsi"].nunique(),
                "detections": len(grp),
            }
            feat["detection_rate"] = feat["detections"] / max(feat["observed_unique"], 1)

            if "operator" in grp.columns:
                op_counts = grp.groupby("operator")["imsi"].nunique()
                feat["operator_diversity"] = int(op_counts.shape[0])
                feat["op_entropy"] = float(
                    -(op_counts / max(op_counts.sum(), 1) * 
                      np.log((op_counts / max(op_counts.sum(), 1)) + 1e-9)).sum()
                )
            else:
                feat["operator_diversity"] = 0
                feat["op_entropy"] = 0.0

            if "cell_id" in grp.columns:
                feat["active_cells"] = int(grp["cell_id"].nunique())
            else:
                feat["active_cells"] = 0

            if "signal_strength" in grp.columns:
                feat["avg_signal"] = float(grp["signal_strength"].mean())
                feat["signal_std"] = float(grp["signal_strength"].std(ddof=0) if len(grp) > 1 else 0.0)
            else:
                feat["avg_signal"] = -75.0
                feat["signal_std"] = 0.0

            if "movement_score" in grp.columns:
                feat["avg_movement"] = float(grp["movement_score"].mean())
            else:
                feat["avg_movement"] = 0.0

            rows.append(feat)

        f = pd.DataFrame(rows).sort_values(["day_of_week", "minute_of_day"]).reset_index(drop=True)
        if f.empty:
            return f

        f["obs_growth"] = f["observed_unique"].diff().fillna(0.0)
        f["rolling_obs_5"] = f["observed_unique"].rolling(5, min_periods=1).mean()
        f["rolling_obs_std_5"] = f["observed_unique"].rolling(5, min_periods=1).std().fillna(0.0)
        return f

    # ---------------------------
    # Training
    # ---------------------------
    def fit_multiplier_model(self, train_df: pd.DataFrame, ground_truth_total_col: str) -> Dict[str, Any]:
        if ground_truth_total_col not in train_df.columns:
            raise ValueError(f"Missing ground truth column: {ground_truth_total_col}")

        feat = self.build_features(train_df)
        if feat.empty:
            raise ValueError("No features generated from training data.")

        if len(feat) < self.cfg.min_training_windows:
            raise ValueError(f"Only {len(feat)} windows. Need {self.cfg.min_training_windows}")

        y_df = train_df.copy()
        y_df["timestamp"] = pd.to_datetime(y_df["timestamp"], errors="coerce")
        y_df["minute"] = y_df["timestamp"].dt.floor("min")
        gt = y_df.groupby("minute")[ground_truth_total_col].max().reset_index(drop=True)

        n = min(len(feat), len(gt))
        feat = feat.iloc[:n].copy()
        gt = gt.iloc[:n].copy()

        observed = feat["observed_unique"].values
        y_multiplier = (gt.values / np.maximum(observed, 1)).astype(float)
        y_multiplier = np.clip(y_multiplier, self.cfg.min_multiplier, self.cfg.max_multiplier)

        X = feat.drop(columns=["observed_unique"]).copy()
        self.feature_columns = list(X.columns)

        X_train, X_val, y_train, y_val = train_test_split(
            X, y_multiplier, test_size=0.2, random_state=self.cfg.random_state
        )

        self.multiplier_model.fit(X_train, y_train)
        pred = self.multiplier_model.predict(X_val)
        mae = mean_absolute_error(y_val, pred)

        self.is_trained = True
        self.save()

        return {
            "status": "trained",
            "samples": int(len(X)),
            "val_mae_multiplier": float(mae),
            "feature_count": len(self.feature_columns)
        }

    # ---------------------------
    # Inference (STABLE VERSION)
    # ---------------------------
    def predict_total(self, live_df: pd.DataFrame) -> Dict[str, Any]:
        if "timestamp" not in live_df.columns or "imsi" not in live_df.columns:
            raise ValueError("live_df must include timestamp and imsi")

        # Update rolling operator prior (fixes bias)
        self._update_operator_prior(live_df)

        observed = int(live_df["imsi"].nunique())
        cr = self.capture_recapture_estimate(live_df)

        feat = self.build_features(live_df)
        if feat.empty:
            return {
                "observed_devices": observed,
                "estimated_total_devices": observed,
                "estimated_unseen_devices": 0,
                "method": "fallback_observed"
            }

        latest = feat.iloc[-1:].copy()

        # Get ML multiplier if trained
        if self.is_trained and self.feature_columns is not None:
            x = latest.drop(columns=["observed_unique"], errors="ignore")
            for c in self.feature_columns:
                if c not in x.columns:
                    x[c] = 0.0
            x = x[self.feature_columns]

            ml_multiplier = float(self.multiplier_model.predict(x)[0])
            ml_multiplier = float(np.clip(ml_multiplier, self.cfg.min_multiplier, self.cfg.max_multiplier))
        else:
            ml_multiplier = cr["cr_multiplier"]

        # STABLE PIPELINE: Single multiplier path
        # 1) Compute raw components
        ml_m = ml_multiplier if self.is_trained else 1.0
        cr_m = cr["cr_multiplier"]

        # 2) Reliability-weighted CR
        cr_reliability = 0.0
        if cr.get("pairs", 0) >= 4 and cr.get("avg_overlap", 0.0) >= 0.15:
            cr_reliability = min(1.0, cr["avg_overlap"] / 0.35)

        # 3) Stable blend (favor ML baseline)
        raw_m = 0.85 * ml_m + 0.15 * (cr_reliability * cr_m + (1 - cr_reliability) * 1.0)

        # 4) Smooth + step-limit (prevents oscillation)
        hybrid_multiplier = self._smooth_multiplier(raw_m)

        # 5) Compute total from ONE multiplier only
        est_total = int(round(observed * hybrid_multiplier))
        unseen = max(0, est_total - observed)

        # 6) Unseen allocation using rolling prior (fixes operator bias)
        unseen_by_operator = {}
        if unseen > 0 and len(self.operator_prior) > 0:
            for op, sh in self.operator_prior.items():
                unseen_by_operator[str(op)] = int(round(unseen * sh))

        return {
            "observed_devices": observed,
            "estimated_total_devices": est_total,
            "estimated_unseen_devices": unseen,
            "ml_multiplier": round(ml_multiplier, 3),
            "capture_recapture_multiplier": round(cr_m, 3),
            "hybrid_multiplier": round(hybrid_multiplier, 3),
            "capture_recapture_pairs": cr["pairs"],
            "cr_avg_overlap": round(cr.get("avg_overlap", 0), 3),
            "cr_reliability": round(cr_reliability, 3),
            "unseen_by_operator_estimate": unseen_by_operator,
            "operator_prior": {k: round(v, 3) for k, v in self.operator_prior.items()},
            "timestamp": pd.Timestamp.utcnow().isoformat()
        }

    # ---------------------------
    # Persistence
    # ---------------------------
    def save(self):
        joblib.dump(self.multiplier_model, os.path.join(self.cfg.model_dir, "multiplier_model.pkl"))
        meta = {
            "feature_columns": self.feature_columns,
            "config": self.cfg.__dict__,
            "is_trained": self.is_trained,
            "last_multiplier": self.last_multiplier,
            "operator_prior": self.operator_prior
        }
        with open(os.path.join(self.cfg.model_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def load(self) -> bool:
        try:
            self.multiplier_model = joblib.load(os.path.join(self.cfg.model_dir, "multiplier_model.pkl"))
            with open(os.path.join(self.cfg.model_dir, "meta.json"), "r") as f:
                meta = json.load(f)
            self.feature_columns = meta.get("feature_columns")
            self.is_trained = bool(meta.get("is_trained", False))
            self.last_multiplier = meta.get("last_multiplier", 1.10)
            self.operator_prior = meta.get("operator_prior", {})
            return True
        except Exception as e:
            print(f"Load failed: {e}")
            return False


if __name__ == "__main__":
    print("="*60)
    print("Hybrid Predictor (Stable) - Ready")
    print(f"  Max Multiplier: 2.2 (capped)")
    print(f"  Smoothing: EWMA (alpha=0.20)")
    print(f"  Step limit: ±8% per cycle")
    print(f"  Operator prior: Rolling EWMA (beta=0.15)")
    print("="*60)
