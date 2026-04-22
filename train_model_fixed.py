#!/usr/bin/env python3
"""
Train AI Model with Your IMSI Data - FIXED VERSION
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
from unified_crowd_model_upgraded import UnifiedCrowdIntelligence

print("="*70)
print("📊 TRAINING AI WITH YOUR IMSI DATA - FIXED")
print("="*70)

# Load your actual IMSI data
print("\n📁 Loading IMSI data from imsi_output.txt...")

data = []
with open("imsi_output.txt", "r") as f:
    lines = f.readlines()
    
for i, line in enumerate(lines):
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
        
        # Create sequential timestamps (spread over last 2 hours)
        timestamp = datetime.now() - timedelta(seconds=(len(lines) - i) * 3)
        
        data.append({
            'timestamp': timestamp,
            'imsi': imsi,
            'operator': operator,
            'cell_id': np.random.randint(1, 10)
        })

if not data:
    print("❌ No data found")
    exit()

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} IMSI records")
print(f"   Unique devices: {df['imsi'].nunique()}")
print(f"   Operators: {df['operator'].unique().tolist()}")
print(f"   Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Initialize AI model
print("\n🤖 Initializing AI model...")
ai = UnifiedCrowdIntelligence()

# Train directly using the train method
print("\n📚 Training AI model on your data...")
print("   This may take a few minutes...\n")

try:
    history = ai.train(df, epochs=20)
    
    if history:
        print("\n✅ Training completed successfully!")
        
        # Test prediction on current data
        print("\n🔮 Making test predictions...")
        result = ai.analyze_current_situation(df)
        
        if result and 'error' not in result:
            print("\n" + "="*70)
            print("🎯 MODEL PREDICTIONS")
            print("="*70)
            print(f"\n📊 Current Devices: {result.get('current_devices', 0)}")
            print(f"🔮 Predicted Devices (next hour): {result.get('predicted_devices', 0)}")
            print(f"📱 Dominant Operator: {result.get('dominant_operator', 'N/A')}")
            print(f"⚠️ Anomaly Detected: {'YES' if result.get('is_anomaly') else 'NO'}")
            
            print(f"\n📈 Operator Forecast:")
            for op, prob in result.get('operator_probabilities', {}).items():
                bar = "█" * int(prob * 50)
                print(f"   {op:10s}: {bar} {prob:.1%}")
            
            print(f"\n💡 Recommendations:")
            for rec in result.get('recommendations', []):
                print(f"   {rec}")
            
            # Save model
            ai.save_models()
            print("\n💾 Model saved to ai_models/ directory")
        else:
            print("⚠️ Prediction test failed")
    else:
        print("❌ Training failed - check data format")
        
except Exception as e:
    print(f"❌ Error during training: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Make sure you have enough data (2500+ records is good)")
    print("   2. Check that timestamps are in correct format")
    print("   3. Ensure all required columns exist")
