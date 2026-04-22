#!/usr/bin/env python3
import pandas as pd
import re
import json
from datetime import datetime, timedelta
from unified_bilstm_model_fixed import CrowdIntelligenceIntegrator, ModelConfig

# Load data
data = []
with open("imsi_output.txt", "r") as f:
    lines = f.readlines()[-500:]

for i, line in enumerate(lines):
    if '410' in line:
        operator = "Telenor" if "Telenor" in line else "Zong" if "Zong" in line else "Ufone" if "Ufone" in line else "Jazz" if "Jazz" in line else "Unknown"
        if operator != "Unknown":
            data.append({
                'timestamp': datetime.now() - timedelta(seconds=i*10),
                'imsi': line[:20],
                'operator': operator,
                'cell_id': 1,
                'signal_strength': -75,
                'movement_score': 0.5
            })

df = pd.DataFrame(data)
print(f"Loaded {len(df)} records")

# Train and predict
config = ModelConfig()
config.epochs = 10
integrator = CrowdIntelligenceIntegrator(config)
result = integrator.process_imsi_data(df)

# Save to file
with open("prediction_output.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"\n✅ Prediction saved to prediction_output.json")
print(f"\n📊 PREDICTION SUMMARY:")
print(f"   Predicted Devices: {result.get('predicted_devices', 'N/A')}")
print(f"   Dominant Operator: {result.get('dominant_operator', 'N/A')}")
print(f"   Anomaly: {result.get('anomaly_probability', 0):.1%}")
