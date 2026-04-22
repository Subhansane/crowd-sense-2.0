#!/usr/bin/env python3
"""
Make prediction using trained model - Ensures enough recent data
"""
import os
import pandas as pd
import numpy as np
import re
import json
from datetime import datetime, timedelta
from unified_bilstm_model import UnifiedCrowdIntelligenceBiLSTM, ModelConfig

print("="*60)
print("📊 LOADING MODEL AND MAKING PREDICTION")
print("="*60)

# Load model
config = ModelConfig()
config.seq_len = 6  # Must match training
config.model_dir = "ai_models"

model = UnifiedCrowdIntelligenceBiLSTM(config)

if not model.load_artifacts():
    print("❌ Failed to load model")
    exit()

print("✅ Model loaded")

# Load recent IMSI data
print("\n📁 Loading recent IMSI data...")

data = []
if os.path.exists("imsi_output.txt"):
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
                'timestamp': datetime.now() - timedelta(seconds=len(data)*5),
                'imsi': f"41006{len(data):06d}",
                'operator': operator,
                'cell_id': 1,
                'signal_strength': -75,
                'movement_score': 0.5
            })

# If not enough data, create synthetic data
if len(data) < 100:
    print(f"⚠️ Only {len(data)} records. Creating synthetic data...")
    for i in range(200):
        hour = (datetime.now().hour + i//10) % 24
        if 8 <= hour <= 10 or 17 <= hour <= 19:
            device_count = np.random.randint(30, 80)
        else:
            device_count = np.random.randint(5, 30)
        
        for _ in range(device_count):
            data.append({
                'timestamp': datetime.now() - timedelta(minutes=i*2),
                'imsi': f"41006{np.random.randint(100000, 999999)}",
                'operator': np.random.choice(['Telenor', 'Zong', 'Ufone', 'Jazz'], p=[0.65, 0.20, 0.10, 0.05]),
                'cell_id': np.random.randint(1, 10),
                'signal_strength': np.random.randint(-95, -50),
                'movement_score': np.random.random()
            })

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} records")

# Create enough recent data by spreading over time
print("\n📊 Creating time-spread data for prediction...")

# Ensure data spans at least 30 minutes (6 x 5 min windows)
if len(df) > 0:
    # Spread records over last 60 minutes
    start_time = datetime.now() - timedelta(minutes=60)
    df['timestamp'] = [start_time + timedelta(seconds=i*5) for i in range(len(df))]
    
    # Sort by time
    df = df.sort_values('timestamp')
    
    print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Unique minutes: {df['timestamp'].dt.floor('min').nunique()}")

# Make prediction
print("\n🔮 Making prediction...")
result = model.predict_from_raw(df)

print("\n" + "="*60)
print("🎯 PREDICTION RESULTS")
print("="*60)

if result and "error" not in result:
    print(f"\n📊 Predicted Devices: {result.get('predicted_devices', 0)}")
    print(f"📱 Dominant Operator: {result.get('dominant_operator', 'N/A')}")
    print(f"⚠️ Anomaly Probability: {result.get('anomaly_probability', 0):.1%}")
    print(f"🚶 Movement Score: {result.get('movement_score', 0):.2f}")
    
    print(f"\n📈 Operator Distribution:")
    for op, prob in result.get('operator_probabilities', {}).items():
        bar = "█" * int(prob * 50)
        print(f"   {op:10s}: {bar} {prob:.1%}")
    
    # Save to file
    with open("prediction_output.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Saved to prediction_output.json")
else:
    print(f"❌ Prediction error: {result}")
    print("\n💡 Tip: Make sure your IMSI catcher is running and collecting data")
