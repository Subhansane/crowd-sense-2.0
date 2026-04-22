#!/usr/bin/env python3
"""
Simplified AI Model for IMSI Crowd Prediction
Works with your existing data format
"""

import pandas as pd
import numpy as np
import re
import joblib
import json
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

print("="*70)
print("🧠 SIMPLIFIED IMSI CROWD AI MODEL")
print("="*70)

class SimpleCrowdAI:
    def __init__(self, model_dir="ai_models_simple"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        self.density_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.anomaly_model = IsolationForest(contamination=0.1, random_state=42)
        self.operator_model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.operator_encoder = LabelEncoder()
        
    def prepare_features(self, df):
        """Extract features from IMSI data"""
        if df.empty:
            return pd.DataFrame()
        
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Create 5-minute windows
        features = []
        
        for i in range(0, len(df), 10):  # Every 10 records = ~1 window
            window_data = df.iloc[i:i+20]
            
            if len(window_data) < 5:
                continue
            
            feat = {}
            
            # Time features
            avg_time = window_data['timestamp'].mean()
            feat['hour'] = avg_time.hour
            feat['minute'] = avg_time.minute
            feat['day_of_week'] = avg_time.weekday()
            
            # Volume features
            feat['device_count'] = window_data['imsi'].nunique()
            feat['detection_count'] = len(window_data)
            feat['detection_rate'] = feat['detection_count'] / max(1, feat['device_count'])
            
            # Operator distribution
            for op in ['Telenor', 'Zong', 'Ufone', 'Jazz']:
                feat[f'op_{op}'] = (window_data['operator'] == op).sum()
            
            feat['operator_diversity'] = window_data['operator'].nunique()
            
            # Cell tower features
            if 'cell_id' in window_data.columns:
                feat['active_cells'] = window_data['cell_id'].nunique()
            else:
                feat['active_cells'] = 1
            
            features.append(feat)
        
        return pd.DataFrame(features)
    
    def train(self, df):
        """Train the model on your IMSI data"""
        print("\n📊 Preparing features...")
        X = self.prepare_features(df)
        
        if X.empty or len(X) < 10:
            print(f"❌ Need more data. Only {len(X)} samples available.")
            return False
        
        print(f"✅ Created {len(X)} training samples")
        
        # Target: next period's device count
        y = X['device_count'].shift(-1).fillna(X['device_count']).values
        X_features = X.drop(['device_count'], axis=1).values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_features)
        
        # Split for training
        split = int(len(X_scaled) * 0.8)
        X_train, X_test = X_scaled[:split], X_scaled[split:]
        y_train, y_test = y[:split], y[split:]
        
        print("📚 Training density prediction model...")
        self.density_model.fit(X_train, y_train)
        
        # Train anomaly detection
        print("📚 Training anomaly detection...")
        self.anomaly_model.fit(X_scaled)
        
        # Train operator model (predict dominant operator)
        print("📚 Training operator model...")
        dominant_ops = X[[c for c in X.columns if c.startswith('op_')]].idxmax(axis=1)
        dominant_ops = dominant_ops.str.replace('op_', '')
        op_encoded = self.operator_encoder.fit_transform(dominant_ops)
        self.operator_model.fit(X_scaled, op_encoded)
        
        # Test accuracy
        train_score = self.density_model.score(X_train, y_train)
        test_score = self.density_model.score(X_test, y_test) if len(y_test) > 0 else 0
        
        print(f"\n✅ Training complete!")
        print(f"   Training R²: {train_score:.3f}")
        print(f"   Test R²: {test_score:.3f}")
        
        # Save model
        self.save()
        return True
    
    def predict(self, df):
        """Make predictions on current data"""
        X = self.prepare_features(df)
        
        if X.empty:
            return None
        
        X_features = X.drop(['device_count'], axis=1).values
        X_scaled = self.scaler.transform(X_features)
        
        # Density prediction
        predicted_devices = self.density_model.predict(X_scaled)[-1]
        
        # Anomaly detection
        anomaly_scores = self.anomaly_model.decision_function(X_scaled)
        is_anomaly = self.anomaly_model.predict(X_scaled)[-1] == -1
        
        # Operator prediction
        op_pred = self.operator_model.predict(X_scaled)[-1]
        dominant_operator = self.operator_encoder.inverse_transform([int(op_pred)])[0]
        
        # Operator probabilities
        op_counts = X[[c for c in X.columns if c.startswith('op_')]].iloc[-1]
        total = op_counts.sum()
        op_probs = {op.replace('op_', ''): count/total for op, count in op_counts.items()}
        
        return {
            'predicted_devices': int(max(0, predicted_devices)),
            'current_devices': int(X['device_count'].iloc[-1]),
            'dominant_operator': dominant_operator,
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_scores[-1]),
            'operator_probabilities': op_probs,
            'confidence': float(1 - abs(anomaly_scores[-1]))
        }
    
    def save(self):
        """Save model to disk"""
        joblib.dump(self.density_model, f"{self.model_dir}/density_model.pkl")
        joblib.dump(self.anomaly_model, f"{self.model_dir}/anomaly_model.pkl")
        joblib.dump(self.operator_model, f"{self.model_dir}/operator_model.pkl")
        joblib.dump(self.scaler, f"{self.model_dir}/scaler.pkl")
        joblib.dump(self.operator_encoder, f"{self.model_dir}/operator_encoder.pkl")
        print(f"💾 Models saved to {self.model_dir}/")
    
    def load(self):
        """Load saved model"""
        try:
            self.density_model = joblib.load(f"{self.model_dir}/density_model.pkl")
            self.anomaly_model = joblib.load(f"{self.model_dir}/anomaly_model.pkl")
            self.operator_model = joblib.load(f"{self.model_dir}/operator_model.pkl")
            self.scaler = joblib.load(f"{self.model_dir}/scaler.pkl")
            self.operator_encoder = joblib.load(f"{self.model_dir}/operator_encoder.pkl")
            print("✅ Model loaded successfully!")
            return True
        except Exception as e:
            print(f"⚠️ No saved model found: {e}")
            return False

# Load your data
print("\n📁 Loading IMSI data from imsi_output.txt...")

data = []
with open("imsi_output.txt", "r") as f:
    lines = f.readlines()
    
for i, line in enumerate(lines):
    if '410' in line and not line.startswith('Nb'):
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
        
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        imsi = imsi_match.group(0) if imsi_match else "unknown"
        
        # Create timestamps spread over last 2 hours
        timestamp = datetime.now() - timedelta(seconds=(len(lines) - i) * 2)
        
        data.append({
            'timestamp': timestamp,
            'imsi': imsi,
            'operator': operator,
            'cell_id': 1
        })

if not data:
    print("❌ No IMSI data found!")
    exit()

df = pd.DataFrame(data)
print(f"✅ Loaded {len(df)} IMSI records")
print(f"   Unique devices: {df['imsi'].nunique()}")
print(f"   Operators: {df['operator'].unique().tolist()}")

# Initialize and train AI
ai = SimpleCrowdAI()

# Try to load existing model
if not ai.load():
    print("\n📚 Training new model on your data...")
    ai.train(df)

# Make predictions
print("\n🔮 Making predictions on current data...")
result = ai.predict(df)

if result:
    print("\n" + "="*70)
    print("🎯 CROWD PREDICTIONS")
    print("="*70)
    print(f"\n📊 Current Devices: {result['current_devices']}")
    print(f"🔮 Predicted Devices (next 5 min): {result['predicted_devices']}")
    print(f"📱 Dominant Operator: {result['dominant_operator']}")
    print(f"⚠️ Anomaly Detected: {'YES' if result['is_anomaly'] else 'NO'}")
    print(f"📈 Confidence: {result['confidence']:.1%}")
    
    print(f"\n📈 Operator Distribution Forecast:")
    for op, prob in sorted(result['operator_probabilities'].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(prob * 50)
        print(f"   {op:10s}: {bar} {prob:.1%}")
    
    print(f"\n💡 Recommendations:")
    if result['predicted_devices'] > 100:
        print("   🔴 High crowd expected - Prepare additional resources")
    elif result['predicted_devices'] > 50:
        print("   🟡 Moderate crowd - Normal operations")
    else:
        print("   🟢 Low crowd - Reduced resources needed")
    
    if result['is_anomaly']:
        print("   ⚠️ Unusual pattern detected - Investigate")
else:
    print("❌ Prediction failed - need more data")
