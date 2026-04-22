#!/usr/bin/env python3
"""
Make predictions using trained hybrid model
"""

import pandas as pd
import re
from datetime import datetime, timedelta
from hybrid_predictor import HybridUnseenDevicePredictor, HybridConfig

print("="*60)
print("🔮 HYBRID UNSEEN DEVICE PREDICTOR")
print("="*60)

# Load model
model = HybridUnseenDevicePredictor(HybridConfig())
if model.load():
    print("✅ Model loaded successfully")
else:
    print("❌ No trained model found. Run train_hybrid.py first")
    exit()

# Load live data from imsi_output.txt
print("\n📁 Loading live IMSI data...")

data = []
with open("imsi_output.txt", "r") as f:
    lines = f.readlines()[-500:]  # Last 500 records

for line in lines:
    if '410' in line and not line.startswith('Nb'):
        operator = "Unknown"
        if "Telenor" in line: operator = "Telenor"
        elif "Zong" in line: operator = "Zong"
        elif "Ufone" in line: operator = "Ufone"
        elif "Jazz" in line: operator = "Jazz"
        else: continue
        
        data.append({
            'timestamp': datetime.now() - timedelta(seconds=len(data)*10),
            'imsi': line[:30],
            'operator': operator,
            'cell_id': 1,
            'signal_strength': -75,
            'movement_score': 0.5
        })

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} records")
print(f"   Unique observed: {df['imsi'].nunique()}")

# Make prediction
print("\n🔮 Predicting unseen devices...")
result = model.predict_total(df)

print("\n" + "="*60)
print("🎯 PREDICTION RESULTS")
print("="*60)

print(f"\n📊 Observed Devices: {result['observed_devices']}")
print(f"📈 Estimated Total: {result['estimated_total_devices']}")
print(f"👻 Estimated Unseen: {result['estimated_unseen_devices']}")
print(f"🔢 ML Multiplier: {result['ml_multiplier']}")
print(f"🔄 CR Multiplier: {result['capture_recapture_multiplier']}")
print(f"⚖️ Hybrid Multiplier: {result['hybrid_multiplier']}")

if result.get('unseen_by_operator_estimate'):
    print(f"\n📱 Unseen by Operator:")
    for op, count in result['unseen_by_operator_estimate'].items():
        print(f"   {op}: ~{count} unseen devices")
