#!/usr/bin/env python3
import pandas as pd
import re
from datetime import datetime, timedelta
from unified_bilstm_model import CrowdIntelligenceIntegrator, ModelConfig

# Load your IMSI data
print("📁 Loading IMSI data...")
data = []
with open("imsi_output.txt", "r") as f:
    lines = f.readlines()[-5000:]  # Last 5000 records

for i, line in enumerate(lines):
    if '410' in line and not line.startswith('Nb'):
        operator = "Unknown"
        if "Telenor" in line: operator = "Telenor"
        elif "Zong" in line: operator = "Zong"
        elif "Ufone" in line: operator = "Ufone"
        elif "Jazz" in line: operator = "Jazz"
        else: continue
        
        data.append({
            'timestamp': datetime.now() - timedelta(seconds=(len(lines)-i)*30),
            'imsi': line[:30],
            'operator': operator,
            'cell_id': 1,
            'signal_strength': -75,
            'movement_score': 0.5
        })

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} records")

# Train BiLSTM model
print("\n🚀 Training BiLSTM model...")
config = ModelConfig()
config.epochs = 30
config.batch_size = 32

integrator = CrowdIntelligenceIntegrator(config)
result = integrator.process_imsi_data(df)

print(f"\n🎯 Prediction: {result}")
