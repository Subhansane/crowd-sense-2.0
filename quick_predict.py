
#!/usr/bin/env python3
"""
Quick prediction using saved BiLSTM model - NO TRAINING NEEDED
"""

import pandas as pd
import re
import json
from datetime import datetime, timedelta
import os

# Import the model class
from unified_bilstm_model import UnifiedCrowdIntelligenceBiLSTM, ModelConfig

print("="*60)
print("📊 LOADING SAVED BILSTM MODEL")
print("="*60)

# Load model (this will NOT retrain)
config = ModelConfig()
config.model_dir = "ai_models"

model = UnifiedCrowdIntelligenceBiLSTM(config)

if model.load_artifacts():
    print("✅ Model loaded successfully!")
else:
    print("❌ Failed to load model")
    exit()

# Load your latest IMSI data
print("\n📁 Loading latest IMSI data...")
data = []

if os.path.exists("imsi_output.txt"):
    with open("imsi_output.txt", "r") as f:
        lines = f.readlines()[-300:]  # Last 300 records
    
    for i, line in enumerate(lines):
        if '410' in line and not line.startswith('Nb'):
            operator = "Unknown"
            if "Telenor" in line: operator = "Telenor"
            elif "Zong" in line: operator = "Zong"
            elif "Ufone" in line: operator = "Ufone"
            elif "Jazz" in line: operator = "Jazz"
            else: continue
            
            data.append({
                'timestamp': datetime.now() - timedelta(seconds=i*15),
                'imsi': f"41006{i:06d}",
                'operator': operator,
                'cell_id': 1,
                'signal_strength': -75,
                'movement_score': 0.5
            })
else:
    print("⚠️ No imsi_output.txt found. Creating sample data...")
    for i in range(200):
        data.append({
            'timestamp': datetime.now() - timedelta(seconds=i*15),
            'imsi': f"41006{i:06d}",
            'operator': "Telenor" if i % 2 == 0 else "Zong",
            'cell_id': 1,
            'signal_strength': -75,
            'movement_score': 0.5
        })

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} records")

# Make prediction (NO TRAINING!)
print("\n🔮 Making prediction with saved model...")
result = model.predict_from_raw(df)

# Display results
print("\n" + "="*60)
print("🎯 PREDICTION RESULTS")
print("="*60)

if result and "error" not in result:
    print(f"\n📊 Predicted Devices: {result.get('predicted_devices', 0)}")
    print(f"📱 Dominant Operator: {result.get('dominant_operator', 'N/A')}")
    print(f"⚠️ Anomaly Probability: {result.get('anomaly_probability', 0):.1%}")
    print(f"🚶 Movement Score: {result.get('movement_score', 0):.2f}")
    
    print(f"\n📈 Operator Distribution Forecast:")
    for op, prob in result.get('operator_probabilities', {}).items():
        bar = "█" * int(prob * 50)
        print(f"   {op:10s}: {bar} {prob:.1%}")
    
    # Save to JSON
    with open("prediction_output.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Prediction saved to prediction_output.json")
else:
    print(f"❌ Prediction error: {result}")
