#!/usr/bin/env python3
"""
Train Hybrid Unseen Device Predictor - PATCHED VERSION
With all safeguards applied
"""

import pandas as pd
import numpy as np
import glob
from hybrid_predictor_patched import HybridUnseenDevicePredictor, HybridConfig

print("="*60)
print("📊 TRAINING HYBRID PREDICTOR (PATCHED)")
print("="*60)

# Load your CSV files
csv_files = glob.glob("imsi_ai_data/**/*.csv", recursive=True)
print(f"Found {len(csv_files)} CSV files")

all_data = []
for f in csv_files[:50]:
    try:
        df = pd.read_csv(f)
        if 'imsi' in df.columns:
            if 'timestamp' not in df.columns:
                df['timestamp'] = pd.date_range('2026-03-01', periods=len(df), freq='min')
            if 'operator' not in df.columns:
                df['operator'] = 'Telenor'
            if 'cell_id' not in df.columns:
                df['cell_id'] = 1
            if 'signal_strength' not in df.columns:
                df['signal_strength'] = -75
            if 'movement_score' not in df.columns:
                df['movement_score'] = 0.5
            
            all_data.append(df)
            print(f"  Loaded: {len(df)} records")
    except Exception as e:
        print(f"  Error: {e}")

if not all_data:
    print("Creating synthetic training data...")
    from datetime import datetime, timedelta
    
    true_pop = np.array([f"imsi_{i:06d}" for i in range(500)])
    ops = ["Telenor", "Zong", "Ufone", "Jazz"]
    
    ts = pd.date_range("2026-03-01 08:00:00", periods=1000, freq="min")
    rows = []
    for t in ts:
        seen_count = np.random.randint(30, 150)
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

# Create synthetic ground truth using capture-recapture
print("\n🔧 Creating synthetic ground truth...")

def estimate_total(df_chunk):
    observed = df_chunk['imsi'].nunique()
    # More conservative multiplier
    if observed < 30:
        multiplier = 1.5
    elif observed < 80:
        multiplier = 1.3
    else:
        multiplier = 1.2
    return int(observed * multiplier)

df['minute'] = pd.to_datetime(df['timestamp']).dt.floor('min')
ground_truth = df.groupby('minute').apply(lambda x: estimate_total(x)).reset_index()
ground_truth.columns = ['minute', 'ground_truth_total']
df = df.merge(ground_truth, on='minute', how='left')
df['ground_truth_total'] = df['ground_truth_total'].fillna(df.groupby('minute')['imsi'].transform('nunique') * 1.3)

print(f"✅ Ground truth created")

# Train with patched config
print("\n🚀 Training hybrid model (patched)...")
config = HybridConfig()
config.max_multiplier = 2.2  # Capped!
config.window_minutes = 5
config.step_minutes = 2
config.min_training_windows = 10

model = HybridUnseenDevicePredictor(config)

try:
    train_info = model.fit_multiplier_model(df, ground_truth_total_col="ground_truth_total")
    print(f"\n✅ Training complete!")
    print(f"   Samples: {train_info['samples']}")
    print(f"   Validation MAE: {train_info['val_mae_multiplier']:.4f}")
    print(f"   Max Multiplier: {config.max_multiplier}")
    
    # Test on recent data
    print("\n🔮 Testing on recent data...")
    recent = df.tail(200)
    result = model.predict_total(recent)
    print(f"   Observed: {result['observed_devices']}")
    print(f"   Estimated Total: {result['estimated_total_devices']}")
    print(f"   Estimated Unseen: {result['estimated_unseen_devices']}")
    print(f"   Hybrid Multiplier: {result['hybrid_multiplier']}")
    print(f"   CR Reliability: {result.get('cr_avg_overlap', 0)}")
    
except Exception as e:
    print(f"❌ Training failed: {e}")
