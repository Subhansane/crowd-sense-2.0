#!/usr/bin/env python3
"""
Hybrid Unseen Device Predictor - PRODUCTION FINAL
With confidence scoring, operator floor, and branch selection
FIXES: Added missing imports, regex IMSI extraction, timestamp preservation
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import re
import time
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from typing import Dict, Any, List
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


@dataclass
class HybridConfig:
    model_dir: str = "hybrid_models"
    window_minutes: int = 2
    step_minutes: int = 1
    ewma_alpha: float = 0.35
    min_multiplier: float = 1.0
    max_multiplier: float = 2.2
    random_state: int = 42
    min_training_windows: int = 30
    min_operator_share: float = 0.05
    cr_reliability_threshold: float = 0.15


class HybridProductionPredictor:
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
        
        # Multiplier smoothing state
        self.last_multiplier = 1.10
        
        # Rolling operator prior
        self.operator_prior = {}
        
        # Confidence tracking
        self.confidence_level = "LOW"
        self.source_branch = "FALLBACK"

    # ---------------------------
    # Helper: Smooth multiplier
    # ---------------------------
    def _smooth_multiplier(self, m_new: float) -> float:
        alpha = 0.20
        m = alpha * m_new + (1 - alpha) * self.last_multiplier
        upper = self.last_multiplier * 1.08
        lower = self.last_multiplier * 0.92
        m = min(max(m, lower), upper)
        m = float(np.clip(m, self.cfg.min_multiplier, self.cfg.max_multiplier))
        self.last_multiplier = m
        return m

    # ---------------------------
    # Helper: Rolling operator prior with floor
    # ---------------------------
    def _update_operator_prior(self, df: pd.DataFrame, all_known_ops=None):
        if "operator" not in df.columns:
            return
        
        op_counts = df.groupby("operator")["imsi"].nunique()
        if op_counts.sum() == 0:
            return
        
        current = (op_counts / op_counts.sum()).to_dict()
        
        beta = 0.15
        all_ops = set(self.operator_prior.keys()) | set(current.keys())
        if all_known_ops:
            all_ops.update(all_known_ops)
        
        for op in all_ops:
            old = self.operator_prior.get(op, 0.0)
            new = current.get(op, 0.0)
            self.operator_prior[op] = (1 - beta) * old + beta * new
        
        # Apply minimum floor share
        for op in self.operator_prior:
            self.operator_prior[op] = max(self.operator_prior[op], self.cfg.min_operator_share)
        
        # Renormalize
        s = sum(self.operator_prior.values())
        if s > 0:
            for op in self.operator_prior:
                self.operator_prior[op] /= s

    # ---------------------------
    # Capture-recapture
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
            if len(w) > 3:
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
                "avg_overlap": 0.0,
                "reliable": False
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
        pairs = len(pair_N)

        if pairs < 4 or avg_overlap < self.cfg.cr_reliability_threshold:
            cr_multiplier = 1.0
            total = observed
            reliable = False
        else:
            total = max(observed, int(round(np.median(pair_N))))
            cr_multiplier = float(np.clip(total / max(observed, 1), 
                                         self.cfg.min_multiplier, 
                                         self.cfg.max_multiplier))
            reliable = True

        total = int(round(observed * cr_multiplier))

        return {
            "observed": observed,
            "cr_estimated_total": total,
            "cr_multiplier": cr_multiplier,
            "pairs": pairs,
            "avg_overlap": avg_overlap,
            "reliable": reliable
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
            else:
                feat["operator_diversity"] = 0

            if "cell_id" in grp.columns:
                feat["active_cells"] = int(grp["cell_id"].nunique())
            else:
                feat["active_cells"] = 0

            feat["avg_movement"] = float(grp["movement_score"].mean()) if "movement_score" in grp.columns else 0.0

            rows.append(feat)

        f = pd.DataFrame(rows).sort_values(["day_of_week", "minute_of_day"]).reset_index(drop=True)
        if f.empty:
            return f

        f["obs_growth"] = f["observed_unique"].diff().fillna(0.0)
        f["rolling_obs_3"] = f["observed_unique"].rolling(3, min_periods=1).mean()
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
            print(f"⚠️ Only {len(feat)} windows, need {self.cfg.min_training_windows}. Training may be weak.")

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
    # Inference with Confidence
    # ---------------------------
    def predict_total(self, live_df: pd.DataFrame) -> Dict[str, Any]:
        if "timestamp" not in live_df.columns or "imsi" not in live_df.columns:
            raise ValueError("live_df must include timestamp and imsi")

        all_ops = live_df["operator"].unique().tolist() if "operator" in live_df.columns else []
        self._update_operator_prior(live_df, all_ops)

        observed = int(live_df["imsi"].nunique())
        cr = self.capture_recapture_estimate(live_df)

        feat = self.build_features(live_df)
        if feat.empty:
            self.source_branch = "FALLBACK"
            self.confidence_level = "LOW"
            return {
                "observed_devices": observed,
                "estimated_total_devices": observed,
                "estimated_unseen_devices": 0,
                "source_branch": "FALLBACK",
                "confidence": "LOW",
                "cr_reliability": 0
            }

        latest = feat.iloc[-1:].copy()

        if self.is_trained and self.feature_columns is not None:
            x = latest.drop(columns=["observed_unique"], errors="ignore")
            for c in self.feature_columns:
                if c not in x.columns:
                    x[c] = 0.0
            x = x[self.feature_columns]
            ml_multiplier = float(self.multiplier_model.predict(x)[0])
            ml_multiplier = float(np.clip(ml_multiplier, self.cfg.min_multiplier, self.cfg.max_multiplier))
        else:
            ml_multiplier = 1.0

        ml_m = ml_multiplier if self.is_trained else 1.0
        cr_m = cr["cr_multiplier"]
        cr_reliability = cr.get("reliable", False)

        if cr_reliability and cr["pairs"] >= 5 and cr["avg_overlap"] >= 0.20:
            self.source_branch = "CR_HIGH"
            self.confidence_level = "HIGH"
            raw_m = 0.6 * ml_m + 0.4 * cr_m
        elif cr_reliability and cr["pairs"] >= 3:
            self.source_branch = "CR_MEDIUM"
            self.confidence_level = "MEDIUM"
            raw_m = 0.75 * ml_m + 0.25 * cr_m
        else:
            self.source_branch = "ML_ONLY"
            self.confidence_level = "MEDIUM" if self.is_trained else "LOW"
            raw_m = ml_m

        hybrid_multiplier = self._smooth_multiplier(raw_m)
        est_total = int(round(observed * hybrid_multiplier))
        unseen = max(0, est_total - observed)

        unseen_by_operator = {}
        if unseen > 0 and len(self.operator_prior) > 0:
            total_allocated = 0
            for op, share in self.operator_prior.items():
                alloc = int(round(unseen * share))
                unseen_by_operator[str(op)] = alloc
                total_allocated += alloc
            
            # remainder correction for rounding
            diff = unseen - total_allocated
            if diff != 0 and unseen_by_operator:
                largest_op = max(unseen_by_operator, key=unseen_by_operator.get)
                unseen_by_operator[largest_op] += diff

        return {
            "observed_devices": observed,
            "estimated_total_devices": est_total,
            "estimated_unseen_devices": unseen,
            "hybrid_multiplier": round(hybrid_multiplier, 3),
            "ml_multiplier": round(ml_multiplier, 3),
            "capture_recapture_multiplier": round(cr_m, 3),
            "cr_pairs": cr["pairs"],
            "cr_avg_overlap": round(cr.get("avg_overlap", 0), 3),
            "cr_reliable": cr_reliability,
            "source_branch": self.source_branch,
            "confidence": self.confidence_level,
            "unseen_by_operator": unseen_by_operator,
            "operator_prior": {k: round(v, 3) for k, v in self.operator_prior.items()},
            "timestamp": datetime.now().isoformat()
        }

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
            return False


# ==========================================
# REAL-TIME PRODUCTION MONITOR
# ==========================================

class ProductionHybridMonitor:
    def __init__(self):
        self.data_buffer = deque(maxlen=5000)
        self.last_position = 0
        
        print("="*70)
        print("🚀 PRODUCTION HYBRID MONITOR (FINAL)")
        print("="*70)
        
        self.model = HybridProductionPredictor(HybridConfig())
        if not self.model.load():
            print("⚠️ No trained model. Running in fallback mode.")
        
        print("✅ Model ready")
        print("📡 Monitoring imsi_output.txt")
        print("="*70)
    
    def parse_line(self, line):
        """Extract IMSI using regex - FIXED"""
        if line.startswith('Nb') or '410' not in line:
            return None
        
        # Use regex to extract clean IMSI (410 + 2 digit MNC + number)
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi = imsi_match.group(0).replace(' ', '')
        
        operator = "Unknown"
        if "Telenor" in line:
            operator = "Telenor"
        elif "Zong" in line:
            operator = "Zong"
        elif "Ufone" in line:
            operator = "Ufone"
        elif "Jazz" in line:
            operator = "Jazz"
        else:
            return None
        
        return {
            'timestamp': datetime.now(),
            'imsi': imsi,
            'operator': operator,
            'cell_id': 1,
            'signal_strength': -75,
            'movement_score': 0.5
        }
    
    def run(self):
        print("\n👀 Waiting for data...\n")
        
        while True:
            try:
                if os.path.exists("imsi_output.txt"):
                    with open("imsi_output.txt", "r") as f:
                        f.seek(self.last_position)
                        lines = f.readlines()
                        self.last_position = f.tell()
                        
                        for line in lines:
                            data = self.parse_line(line)
                            if data:
                                self.data_buffer.append(data)
                
                if len(self.data_buffer) > 100:
                    df = pd.DataFrame(list(self.data_buffer))
                    
                    # CRITICAL FIX: Preserve original timestamps, don't overwrite!
                    if "timestamp" in df.columns:
                        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
                    
                    result = self.model.predict_total(df)
                    
                    conf_symbol = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(result['confidence'], "⚪")
                    
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {conf_symbol} Confidence: {result['confidence']} | Branch: {result['source_branch']}")
                    print(f"   Observed: {result['observed_devices']} → Total: ~{result['estimated_total_devices']} (+{result['estimated_unseen_devices']} unseen)")
                    print(f"   Multiplier: {result['hybrid_multiplier']} (ML: {result['ml_multiplier']}, CR: {result['capture_recapture_multiplier']})")
                    print(f"   CR: pairs={result['cr_pairs']}, overlap={result['cr_avg_overlap']}, reliable={result['cr_reliable']}")
                    
                    if result.get('unseen_by_operator'):
                        print(f"   Unseen breakdown: {result['unseen_by_operator']}")
                
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n👋 Monitor stopped")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    monitor = ProductionHybridMonitor()
    monitor.run()
