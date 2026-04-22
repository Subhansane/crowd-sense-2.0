#!/usr/bin/env python3
"""
Train BiLSTM model on ALL CSV files in imsi_ai_data folder
"""

import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime, timedelta
from unified_bilstm_model import UnifiedCrowdIntelligenceBiLSTM, ModelConfig

print("="*70)
print("📊 TRAINING BILSTM ON ALL CSV FILES")
print("="*70)

# Find all CSV files
csv_files = []
csv_files.extend(glob.glob("imsi_ai_data/**/*.csv", recursive=True))
csv_files.extend(glob.glob("imsi_ai_data/*.csv", recursive=True))

# Also look for simple format files
csv_files.extend(glob.glob("imsi_ai_data/**/*_simple.txt", recursive=True))

print(f"📁 Found {len(csv_files)} CSV files")

# Load and combine all data
all_data = []

for filepath in csv_files[:100]:  # Limit to 100 files for performance
    try:
        print(f"   Loading: {os.path.basename(filepath)}")
        
        # Try reading CSV
        try:
            df = pd.read_csv(filepath)
        except:
            # Try reading as text
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Parse lines
            data = []
            for line in lines:
                if '410' in line:
                    parts = line.split(',')
                    if len(parts) >= 3:
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
            
            # Add required columns if missing
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
    print("\n❌ No valid IMSI data found in CSV files!")
    print("   Creating sample data for training...")
    
    # Create sample data
    np.random.seed(42)
    n_samples = 2000
    
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(days=7),
        periods=n_samples,
        freq='5min'
    )
    
    for ts in timestamps:
        hour = ts.hour
        # Simulate rush hour patterns
        if 8 <= hour <= 10 or 17 <= hour <= 19:
            device_count = np.random.randint(50, 150)
        else:
            device_count = np.random.randint(10, 50)
        
        for _ in range(device_count):
            all_data.append(pd.DataFrame({
                'timestamp': [ts],
                'imsi': [f"41006{np.random.randint(100000, 999999)}"],
                'operator': [np.random.choice(['Telenor', 'Zong', 'Ufone', 'Jazz'], p=[0.65, 0.20, 0.10, 0.05])],
                'cell_id': [np.random.randint(1, 10)],
                'signal_strength': [np.random.randint(-95, -50)],
                'movement_score': [np.random.random()]
            }))

# Combine all data
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 TOTAL DATA: {len(combined_df)} records")
    print(f"   Unique IMSIs: {combined_df['imsi'].nunique()}")
    print(f"   Time range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
    print(f"   Operators: {combined_df['operator'].unique().tolist()}")
else:
    print("❌ No data to train on!")
    exit()

# Train the model
print("\n🚀 Training BiLSTM model on ALL CSV data...")
config = ModelConfig()
config.epochs = 50
config.batch_size = 64
config.model_dir = "ai_models"

model = UnifiedCrowdIntelligenceBiLSTM(config)

# Train
history = model.train(combined_df)

if history:
    print("\n✅ TRAINING COMPLETE!")
    print(f"   Final training loss: {history.history['loss'][-1]:.4f}")
    
    # Save the trained model
    model.save_artifacts(list(model.feature_scaler.mean_.keys()) if hasattr(model.feature_scaler, 'mean_') else [])
    print("💾 Model saved to ai_models/")
    
    # Make a test prediction
    print("\n🔮 Making test prediction on recent data...")
    recent_df = combined_df.tail(200)
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
else:
    print("❌ Training failed!")
