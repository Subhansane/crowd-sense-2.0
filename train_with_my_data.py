#!/usr/bin/env python3
"""
Train AI Model with Your Actual IMSI Data
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from unified_crowd_model_upgraded import CrowdIntelligenceIntegrator

print("="*70)
print("📊 TRAINING AI WITH YOUR IMSI DATA")
print("="*70)

# Load your actual IMSI data from imsi_output.txt
print("\n📁 Loading IMSI data from imsi_output.txt...")

data = []
with open("imsi_output.txt", "r") as f:
    for line in f:
        if '410' in line and not line.startswith('Nb'):
            # Extract operator
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
                continue
            
            # Extract IMSI
            imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
            imsi = imsi_match.group(0) if imsi_match else "unknown"
            
            # Create timestamp (use current time or parse from line)
            timestamp = datetime.now()
            
            data.append({
                'timestamp': timestamp,
                'imsi': imsi,
                'operator': operator,
                'cell_id': 1  # Default cell ID
            })

if not data:
    print("❌ No data found in imsi_output.txt")
    print("   Make sure your IMSI catcher is running and capturing data")
    exit()

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} IMSI records")
print(f"   Unique devices: {df['imsi'].nunique()}")
print(f"   Operators: {df['operator'].unique().tolist()}")

# Initialize AI
print("\n🤖 Initializing AI model...")
ai = CrowdIntelligenceIntegrator()

# Train the model
print("\n📚 Training AI model on your data...")
result = ai.process_imsi_data(df)

if result:
    print("\n" + "="*70)
    print("🎯 TRAINING COMPLETE - RESULTS")
    print("="*70)
    print(f"\n📊 Current Status:")
    print(f"   Devices: {result.get('current_devices', 0)}")
    print(f"   Active Operators: {result.get('active_operators', [])}")
    
    print(f"\n🔮 Predictions:")
    print(f"   Expected Devices: {result.get('predicted_devices', 0)}")
    print(f"   Dominant Operator: {result.get('dominant_operator', 'N/A')}")
    print(f"   Confidence: {result.get('density_confidence', 0):.1%}")
    
    print(f"\n📈 Operator Probabilities:")
    for op, prob in result.get('operator_probabilities', {}).items():
        bar = "█" * int(prob * 50)
        print(f"   {op:10s}: {bar} {prob:.1%}")
    
    print(f"\n💡 Recommendations:")
    for rec in result.get('recommendations', []):
        print(f"   {rec}")
    
    print("\n✅ Model saved to ai_models/ directory")
else:
    print("\n⚠️ Need more data for training. Continue running IMSI catcher.")
    print(f"   Current records: {len(df)}. Recommended: 500+ records")

