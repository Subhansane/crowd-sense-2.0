#!/usr/bin/env python3
"""
Unified IMSI Crowd Intelligence Model (BiLSTM Edition)

Tasks:
1) Crowd density prediction (regression)
2) Anomaly detection (binary classification)
3) Dominant operator forecast (multi-class classification)
4) Movement score prediction (regression)

Key upgrades:
- Shared BiLSTM backbone for temporal learning
- Optional attention pooling
- Proper sequence dataset creation
- Stronger error handling and logging
"""

import os
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from collections import deque

import numpy as np
import pandas as pd
import joblib
import tensorflow as tf

from tensorflow.keras import layers, models, callbacks
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN


# -------------------------
# Config
# -------------------------
@dataclass
class ModelConfig:
    operators: tuple = ("Telenor", "Zong", "Ufone", "Jazz")
    model_dir: str = "ai_models"
    buffer_size: int = 5000

    # Sequence/model params
    seq_len: int = 12
    bilstm_units: int = 64
    dense_units: int = 64
    dropout: float = 0.25
    use_attention: bool = True

    # Training
    epochs: int = 60
    batch_size: int = 64
    validation_split: float = 0.2
    learning_rate: float = 1e-3

    # Aux models
    contamination: float = 0.08  # anomaly ratio for IsolationForest

    # Runtime
    enable_mixed_precision: bool = False


class UnifiedCrowdIntelligenceBiLSTM:
    def __init__(self, config: ModelConfig = ModelConfig()):
        self.cfg = config
        os.makedirs(self.cfg.model_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        self.logger = logging.getLogger("UnifiedCrowdIntelligenceBiLSTM")

        if self.cfg.enable_mixed_precision:
            try:
                tf.keras.mixed_precision.set_global_policy("mixed_float16")
                self.logger.info("Mixed precision enabled.")
            except Exception as e:
                self.logger.warning(f"Could not enable mixed precision: {e}")

        self.feature_scaler = StandardScaler()
        self.operator_encoder = LabelEncoder()

        self.unified_model = None
        self.anomaly_model = IsolationForest(
            contamination=self.cfg.contamination, random_state=42
        )
        self.cluster_model = DBSCAN(eps=0.7, min_samples=8)
        self.training_history = {}

        self.logger.info("BiLSTM crowd intelligence model initialized.")

    # -------------------------
    # Feature engineering
    # -------------------------
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate IMSI events into minute-level feature rows.
        """
        required_cols = {"timestamp", "imsi"}
        if df.empty or not required_cols.issubset(df.columns):
            self.logger.error("Input data is empty or missing required columns.")
            return pd.DataFrame()

        x = df.copy()
        x["minute"] = pd.to_datetime(x["timestamp"], errors="coerce").dt.floor("min")
        x = x.dropna(subset=["minute"])
        grouped = x.groupby("minute", sort=True)

        rows = []
        for minute, g in grouped:
            feat = {}
            # Time
            feat["hour"] = minute.hour
            feat["minute_of_day"] = minute.hour * 60 + minute.minute
            feat["day_of_week"] = minute.weekday()
            feat["is_weekend"] = 1 if feat["day_of_week"] >= 5 else 0

            # Volume
            feat["total_devices"] = g["imsi"].nunique()
            feat["total_detections"] = len(g)
            feat["detection_rate"] = feat["total_detections"] / max(feat["total_devices"], 1)

            # Operator distribution
            op_series = g["operator"] if "operator" in g.columns else pd.Series([], dtype=str)
            for op in self.cfg.operators:
                feat[f"operator_{op}"] = int((op_series == op).sum())
            feat["operator_diversity"] = int(op_series.nunique()) if len(op_series) else 0

            # Cell / geo
            cell_series = g["cell_id"] if "cell_id" in g.columns else pd.Series([], dtype="float")
            feat["active_cells"] = int(cell_series.nunique()) if len(cell_series) else 0
            feat["cell_density"] = feat["active_cells"] / max(feat["total_devices"], 1)

            # Movement/signal
            feat["avg_movement"] = float(g["movement_score"].mean()) if "movement_score" in g.columns else 0.0
            if "signal_strength" in g.columns:
                feat["avg_signal"] = float(g["signal_strength"].mean())
                feat["signal_variance"] = float(g["signal_strength"].std(ddof=0) if len(g) > 1 else 0.0)
            else:
                feat["avg_signal"] = -75.0
                feat["signal_variance"] = 4.0

            rows.append(feat)

        feats = pd.DataFrame(rows).sort_index()

        if feats.empty:
            return feats

        # Lag/rolling features
        feats["device_growth"] = feats["total_devices"].diff().fillna(0.0)
        feats["detection_trend"] = feats["detection_rate"].diff().fillna(0.0)
        feats["rolling_avg_5min"] = feats["total_devices"].rolling(5, min_periods=1).mean()
        feats["rolling_std_5min"] = feats["total_devices"].rolling(5, min_periods=1).std().fillna(0.0)

        return feats

    # -------------------------
    # Sequence preparation
    # -------------------------
    def _make_sequences(self, X_2d, y_density, y_anomaly, y_operator_cat, y_movement, seq_len):
        X_seq, d_seq, a_seq, o_seq, m_seq = [], [], [], [], []
        for i in range(seq_len, len(X_2d)):
            X_seq.append(X_2d[i-seq_len:i])
            d_seq.append(y_density[i])
            a_seq.append(y_anomaly[i])
            o_seq.append(y_operator_cat[i])
            m_seq.append(y_movement[i])
        return (
            np.asarray(X_seq, dtype=np.float32),
            np.asarray(d_seq, dtype=np.float32),
            np.asarray(a_seq, dtype=np.float32),
            np.asarray(o_seq, dtype=np.float32),
            np.asarray(m_seq, dtype=np.float32),
        )

    def prepare_training_data(self, df: pd.DataFrame):
        feats = self.extract_features(df)
        if feats.empty or len(feats) <= self.cfg.seq_len + 5:
            self.logger.error("Not enough feature rows for sequence training.")
            return None

        # Feature columns (exclude direct label leakage columns if needed)
        feature_cols = [c for c in feats.columns]

        X = feats[feature_cols].astype(np.float32).values
        X_scaled = self.feature_scaler.fit_transform(X)

        # Labels
        y_density = feats["total_devices"].astype(np.float32).values

        # FIXED anomaly label bug:
        # anomaly = 1 if above 95th percentile
        th = np.quantile(y_density, 0.95)
        y_anomaly = (y_density > th).astype(np.float32)

        op_cols = [f"operator_{op}" for op in self.cfg.operators]
        dominant_ops = feats[op_cols].idxmax(axis=1).str.replace("operator_", "", regex=False).values
        y_op_enc = self.operator_encoder.fit_transform(dominant_ops)
        y_operator_cat = tf.keras.utils.to_categorical(y_op_enc, num_classes=len(self.cfg.operators)).astype(np.float32)

        # next-step movement target
        y_movement = feats["avg_movement"].shift(-1).ffill().fillna(0).astype(np.float32).values

        X_seq, yd, ya, yo, ym = self._make_sequences(
            X_scaled, y_density, y_anomaly, y_operator_cat, y_movement, self.cfg.seq_len
        )

        self.logger.info(f"Prepared sequences: X={X_seq.shape}, density={yd.shape}")
        return X_seq, yd, ya, yo, ym, feature_cols

    # -------------------------
    # Model
    # -------------------------
    def build_model(self, n_features: int):
        inp = layers.Input(shape=(self.cfg.seq_len, n_features), name="sequence_input")

        x = layers.Masking(mask_value=0.0)(inp)
        x = layers.Bidirectional(
            layers.LSTM(self.cfg.bilstm_units, return_sequences=True),
            name="bilstm_1"
        )(x)
        x = layers.Dropout(self.cfg.dropout)(x)

        x = layers.Bidirectional(
            layers.LSTM(self.cfg.bilstm_units // 2, return_sequences=True),
            name="bilstm_2"
        )(x)

        if self.cfg.use_attention:
            attn = layers.MultiHeadAttention(num_heads=4, key_dim=16, name="mha")(x, x)
            x = layers.Add()([x, attn])
            x = layers.LayerNormalization()(x)

        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(self.cfg.dense_units, activation="relu")(x)
        x = layers.Dropout(self.cfg.dropout)(x)

        # Heads
        density = layers.Dense(32, activation="relu")(x)
        density = layers.Dense(1, name="density_prediction")(density)

        anomaly = layers.Dense(32, activation="relu")(x)
        anomaly = layers.Dense(1, activation="sigmoid", name="anomaly_detection")(anomaly)

        operator = layers.Dense(32, activation="relu")(x)
        operator = layers.Dense(len(self.cfg.operators), activation="softmax", name="operator_forecast")(operator)

        movement = layers.Dense(32, activation="relu")(x)
        movement = layers.Dense(1, name="movement_prediction")(movement)

        model = models.Model(inputs=inp, outputs=[density, anomaly, operator, movement], name="UnifiedBiLSTM")

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.cfg.learning_rate),
            loss={
                "density_prediction": "mse",
                "anomaly_detection": "binary_crossentropy",
                "operator_forecast": "categorical_crossentropy",
                "movement_prediction": "mse",
            },
            metrics={
                "density_prediction": ["mae"],
                "anomaly_detection": ["accuracy", tf.keras.metrics.AUC(name="auc")],
                "operator_forecast": ["accuracy"],
                "movement_prediction": ["mae"],
            },
            # You can tune these
            loss_weights={
                "density_prediction": 1.0,
                "anomaly_detection": 1.2,
                "operator_forecast": 1.0,
                "movement_prediction": 0.8,
            },
        )

        self.unified_model = model
        self.logger.info("BiLSTM unified model built.")
        return model

    # -------------------------
    # Train / predict
    # -------------------------
    def train(self, df: pd.DataFrame):
        prepared = self.prepare_training_data(df)
        if prepared is None:
            return None

        X, y_density, y_anomaly, y_operator, y_movement, feature_cols = prepared
        self.build_model(n_features=X.shape[-1])

        cbs = [
            callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
            callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4),
            callbacks.ModelCheckpoint(
                os.path.join(self.cfg.model_dir, "unified_bilstm.keras"),
                monitor="val_loss",
                save_best_only=True
            ),
        ]

        hist = self.unified_model.fit(
            X,
            {
                "density_prediction": y_density,
                "anomaly_detection": y_anomaly,
                "operator_forecast": y_operator,
                "movement_prediction": y_movement,
            },
            epochs=self.cfg.epochs,
            batch_size=self.cfg.batch_size,
            validation_split=self.cfg.validation_split,
            callbacks=cbs,
            verbose=1,
        )

        self.training_history = hist.history

        # Fit auxiliary models on flattened sequences
        X_flat = X.reshape(X.shape[0], -1)
        self.anomaly_model.fit(X_flat)
        self.cluster_model.fit(X_flat)

        self.save_artifacts(feature_cols)
        self.logger.info("Training complete.")
        return hist

    def _prepare_inference_sequence(self, feature_df: pd.DataFrame):
        if len(feature_df) < self.cfg.seq_len:
            return None
        X_all = self.feature_scaler.transform(feature_df.astype(np.float32).values)
        X_last = X_all[-self.cfg.seq_len:]  # (seq_len, n_features)
        return np.expand_dims(X_last, axis=0).astype(np.float32)  # (1, seq_len, n_features)

    def predict_from_raw(self, raw_df: pd.DataFrame):
        if self.unified_model is None:
            self.logger.error("Model is not loaded/trained.")
            return None

        feats = self.extract_features(raw_df)
        if feats.empty:
            return {"error": "Insufficient data for features"}

        X_seq = self._prepare_inference_sequence(feats)
        if X_seq is None:
            return {"error": f"Need at least {self.cfg.seq_len} minute-level rows"}

        d_pred, a_pred, o_pred, m_pred = self.unified_model.predict(X_seq, verbose=0)

        X_flat = X_seq.reshape(1, -1)
        iso_score = float(self.anomaly_model.decision_function(X_flat)[0])
        iso_flag = bool(self.anomaly_model.predict(X_flat)[0] == -1)

        op_idx = int(np.argmax(o_pred[0]))
        op_name = self.operator_encoder.inverse_transform([op_idx])[0]

        return {
            "predicted_devices": int(max(0, d_pred[0][0])),
            "anomaly_probability": float(a_pred[0][0]),
            "is_anomaly": iso_flag,
            "anomaly_score": iso_score,
            "dominant_operator": op_name,
            "operator_probabilities": {
                op: float(prob) for op, prob in zip(self.operator_encoder.classes_, o_pred[0])
            },
            "movement_score": float(m_pred[0][0]),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    # -------------------------
    # Persistence
    # -------------------------
    def save_artifacts(self, feature_cols):
        self.unified_model.save(os.path.join(self.cfg.model_dir, "unified_bilstm.keras"))
        joblib.dump(self.feature_scaler, os.path.join(self.cfg.model_dir, "feature_scaler.pkl"))
        joblib.dump(self.operator_encoder, os.path.join(self.cfg.model_dir, "operator_encoder.pkl"))
        joblib.dump(self.anomaly_model, os.path.join(self.cfg.model_dir, "anomaly_model.pkl"))
        joblib.dump(self.cluster_model, os.path.join(self.cfg.model_dir, "cluster_model.pkl"))

        meta = {
            "feature_columns": feature_cols,
            "config": self.cfg.__dict__,
            "training_history_keys": list(self.training_history.keys()),
        }
        with open(os.path.join(self.cfg.model_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        self.logger.info("Artifacts saved.")

    def load_artifacts(self):
        try:
            self.unified_model = models.load_model(os.path.join(self.cfg.model_dir, "unified_bilstm.keras"))
            self.feature_scaler = joblib.load(os.path.join(self.cfg.model_dir, "feature_scaler.pkl"))
            self.operator_encoder = joblib.load(os.path.join(self.cfg.model_dir, "operator_encoder.pkl"))
            self.anomaly_model = joblib.load(os.path.join(self.cfg.model_dir, "anomaly_model.pkl"))
            self.cluster_model = joblib.load(os.path.join(self.cfg.model_dir, "cluster_model.pkl"))
            self.logger.info("Artifacts loaded successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load artifacts: {e}")
            return False


class CrowdIntelligenceIntegrator:
    def __init__(self, config: ModelConfig = ModelConfig()):
        self.model = UnifiedCrowdIntelligenceBiLSTM(config=config)
        self.buffer = deque(maxlen=config.buffer_size)

        if not self.model.load_artifacts():
            self.model.logger.warning("No trained model found yet; train() will be required.")

    def process_imsi_data(self, new_df: pd.DataFrame):
        if new_df is None or new_df.empty:
            return None

        for row in new_df.to_dict("records"):
            self.buffer.append(row)

        buf_df = pd.DataFrame(list(self.buffer))
        if buf_df.empty:
            return None

        # Auto-train if needed and enough data exists
        if self.model.unified_model is None and len(buf_df) > 500:
            self.model.logger.info("Auto-training BiLSTM model...")
            self.model.train(buf_df)

        if self.model.unified_model is None:
            return {"status": "collecting_data", "rows_in_buffer": len(buf_df)}

        pred = self.model.predict_from_raw(buf_df)
        if isinstance(pred, dict) and "error" not in pred:
            pred["current_devices"] = int(buf_df["imsi"].nunique()) if "imsi" in buf_df.columns else 0
            pred["active_cells"] = int(buf_df["cell_id"].nunique()) if "cell_id" in buf_df.columns else 0
        return pred


if __name__ == "__main__":
    # Demo
    np.random.seed(42)

    sample = pd.DataFrame({
        "timestamp": pd.date_range("2026-04-05 10:00:00", periods=1200, freq="min"),
        "imsi": np.random.choice([f"41006{i:06d}" for i in range(300)], size=1200),
        "operator": np.random.choice(["Telenor", "Zong", "Ufone", "Jazz"], size=1200),
        "cell_id": np.random.randint(1, 25, size=1200),
        "signal_strength": np.random.randint(-95, -50, size=1200),
        "movement_score": np.random.rand(1200),
    })

    integrator = CrowdIntelligenceIntegrator()
    if integrator.model.unified_model is None:
        integrator.model.train(sample)

    result = integrator.process_imsi_data(sample.tail(400))
    print("\nPrediction Output:\n", json.dumps(result, indent=2))
