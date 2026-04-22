#!/usr/bin/env python3
"""
Train BiLSTM model on ALL CSV files - FIXED for smaller datasets
"""

import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime, timedelta
from unified_bilstm_model import UnifiedCrowdIntelligenceBiLSTM, ModelConfig

print("="*70)
print("📊 TRAINING BILSTM ON ALL CSV FILES (FIXED)")
print("="*70)

# Find all CSV files
csv_files = []
csv_files.extend(glob.glob("imsi_ai_data/**/*.csv", recursive=True))
csv_files.extend(glob.glob("imsi_ai_data/*.csv", recursive=True))
csv_files.extend(glob.glob("imsi_ai_data/**/*_simple.txt", recursive=True))

print(f"📁 Found {len(csv_files)} files")

# Load and combine all data
all_data = []

for filepath in csv_files:
    try:
        print(f"   Loading: {os.path.basename(filepath)}")
        
        # Try reading CSV
        try:
            df = pd.read_csv(filepath)
        except:
            # Try reading as text
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            data = []
            for line in lines:
                if '410' in line:
                    parts = line.split(',')
                    operator = "Unknown"
                    if "Telenor" in line: operator = "Telenor"
                    elif "Zong" in line: operator = "Zong"
                    elif "Ufone" in line: operator = "Ufone"
                    elif "Jazz" in line: operator = "Jazz"
                    
                    data.append({
                        'timestamp': datetime.now() - timedelta(seconds=len(data)),
                        'imsi': parts[0] if len(parts) > 0 else line[:20],
                        'operator': operator,
                        'cell_id': 1,
                        'signal_strength': -75,
                        'movement_score': 0.5
                    })
            df = pd.DataFrame(data)
        
        # Check if it has IMSI data
        if 'imsi' in df.columns or 'IMSI' in df.columns:
            if 'IMSI' in df.columns:
                df = df.rename(columns={'IMSI': 'imsi'})
            
            if 'timestamp' not in df.columns:
                df['timestamp'] = datetime.now()
            if 'operator' not in df.columns:
                df['operator'] = 'Telenor'
            if 'cell_id' not in df.columns:
                df['cell_id'] = 1
            if 'signal_strength' not in df.columns:
                df['signal_strength'] = -75
            if 'movement_score' not in df.columns:
                df['movement_score'] = 0.5
            
            all_data.append(df)
            print(f"      ✅ Added {len(df)} records")
            
    except Exception as e:
        print(f"      ⚠️ Error: {e}")

if not all_data:
    print("\n❌ No valid IMSI data found!")
    exit()

# Combine all data
combined_df = pd.concat(all_data, ignore_index=True)
print(f"\n📊 TOTAL DATA: {len(combined_df)} records")
print(f"   Unique IMSIs: {combined_df['imsi'].nunique()}")
print(f"   Time range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
print(f"   Operators: {combined_df['operator'].unique().tolist()}")

# Create custom config for smaller dataset
print("\n🚀 Training BiLSTM model with adjusted parameters...")

# Create custom config with smaller sequence length
config = ModelConfig()
config.epochs = 30
config.batch_size = 16
config.seq_len = 6  # Reduced from 12 to 6 (works with smaller dataset)
config.bilstm_units = 32  # Reduced from 64
config.dense_units = 32  # Reduced from 64
config.model_dir = "ai_models"
config.buffer_size = 2000

print(f"   Sequence length: {config.seq_len}")
print(f"   BiLSTM units: {config.bilstm_units}")
print(f"   Epochs: {config.epochs}")

# Initialize model
model = UnifiedCrowdIntelligenceBiLSTM(config)

# Train
try:
    history = model.train(combined_df)
    
    if history:
        print("\n✅ TRAINING COMPLETE!")
        print(f"   Final loss: {history.history['loss'][-1]:.4f}")
        
        # Make test prediction
        print("\n🔮 Making test prediction...")
        recent_df = combined_df.tail(100)
        result = model.predict_from_raw(recent_df)
        
        if result and "error" not in result:
            print("\n" + "="*60)
            print("🎯 TEST PREDICTION")
            print("="*60)
            print(f"   Predicted Devices: {result.get('predicted_devices', 0)}")
            print(f"   Dominant Operator: {result.get('dominant_operator', 'N/A')}")
            print(f"   Anomaly Probability: {result.get('anomaly_probability', 0):.1%}")
            
            print(f"\n   Operator Distribution:")
            for op, prob in result.get('operator_probabilities', {}).items():
                bar = "█" * int(prob * 50)
                print(f"      {op}: {bar} {prob:.1%}")
            
            # Save prediction
            import json
            with open("prediction_output.json", "w") as f:
                json.dump(result, f, indent=2)
            print("\n💾 Prediction saved to prediction_output.json")
        else:
            print(f"   Prediction: {result}")
    else:
        print("❌ Training failed")
        
except Exception as e:
    print(f"❌ Error during training: {e}")
    print("\n💡 Try collecting more IMSI data first!")
