#!/usr/bin/env python3
"""
Train Hybrid Unseen Device Predictor on your IMSI CSV data
"""

import pandas as pd
import glob
from hybrid_predictor import HybridUnseenDevicePredictor, HybridConfig

print("="*60)
print("📊 TRAINING HYBRID UNSEEN DEVICE PREDICTOR")
print("="*60)

# Load all your CSV files
csv_files = glob.glob("imsi_ai_data/**/*.csv", recursive=True)
print(f"Found {len(csv_files)} CSV files")

all_data = []
for f in csv_files[:50]:  # Limit to 50 files
    try:
        df = pd.read_csv(f)
        if 'imsi' in df.columns:
            all_data.append(df)
            print(f"  Loaded: {len(df)} records")
    except:
        pass

if not all_data:
    print("Creating synthetic training data...")
    import numpy as np
    from datetime import datetime, timedelta
    
    true_pop = np.array([f"imsi_{i:06d}" for i in range(1000)])
    ops = ["Telenor", "Zong", "Ufone", "Jazz"]
    
    ts = pd.date_range("2026-03-01 08:00:00", periods=1000, freq="min")
    rows = []
    for t in ts:
        seen_count = np.random.randint(50, 200)
        seen = np.random.choice(true_pop, size=seen_count, replace=False)
        for imsi in seen:
            rows.append({
                "timestamp": t,
                "imsi": imsi,
                "operator": np.random.choice(ops, p=[0.65, 0.20, 0.10, 0.05]),
                "cell_id": np.random.randint(1, 10),
                "signal_strength": np.random.randint(-95, -50),
                "movement_score": np.random.random(),
                "ground_truth_total": len(true_pop)
            })
    all_data = [pd.DataFrame(rows)]

df = pd.concat(all_data, ignore_index=True)
print(f"\n📊 Total training data: {len(df)} records")
print(f"   Unique IMSIs: {df['imsi'].nunique()}")

# Train model
print("\n🚀 Training hybrid model...")
model = HybridUnseenDevicePredictor(HybridConfig())
train_info = model.fit_multiplier_model(df, ground_truth_total_col="ground_truth_total")

print(f"\n✅ Training complete!")
print(f"   Samples: {train_info['samples']}")
print(f"   Validation MAE: {train_info['val_mae_multiplier']:.4f}")
