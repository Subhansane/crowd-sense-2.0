#!/usr/bin/env python3
"""
Unified IMSI Crowd Intelligence Model
Combines: Density Prediction, Anomaly Detection, Operator Forecast, Movement Patterns
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import joblib
import json
import os

# TensorFlow/Keras for deep learning
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

# Scikit-learn for traditional ML
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import DBSCAN

class UnifiedCrowdIntelligence:
    """
    Single model that does it all:
    1. Predict crowd density (regression)
    2. Detect anomalies (binary classification)
    3. Forecast operator market share (multi-class)
    4. Predict device movement (sequence prediction)
    5. Cluster behavior patterns (unsupervised)
    """
    
    def __init__(self, model_dir="ai_models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize all sub-models
        self.density_model = None      # Predicts crowd size
        self.anomaly_model = None      # Detects unusual patterns
        self.operator_model = None     # Predicts operator distribution
        self.movement_model = None     # Predicts cell tower transitions
        self.cluster_model = None      # Groups similar behaviors
        
        # Scalers and encoders
        self.feature_scaler = StandardScaler()
        self.operator_encoder = LabelEncoder()
        self.cell_encoder = LabelEncoder()
        
        # Training history
        self.training_history = []
        
        print("="*70)
        print("🧠 UNIFIED IMSI CROWD INTELLIGENCE MODEL")
        print("="*70)
    
    def extract_features(self, df):
        """
        Extract rich features from IMSI data
        """
        if df.empty:
            return pd.DataFrame()
        
        features = []
        
        # Group by timestamp (minute-level aggregation)
        df['minute'] = pd.to_datetime(df['timestamp']).dt.floor('min')
        grouped = df.groupby('minute')
        
        for minute, group in grouped:
            feat = {}
            
            # Time features
            feat['hour'] = minute.hour
            feat['minute_of_day'] = minute.hour * 60 + minute.minute
            feat['day_of_week'] = minute.weekday()
            feat['is_weekend'] = 1 if feat['day_of_week'] >= 5 else 0
            
            # Volume features
            feat['total_devices'] = group['imsi'].nunique()
            feat['total_detections'] = len(group)
            feat['detection_rate'] = len(group) / max(1, feat['total_devices'])
            
            # Operator distribution
            for op in ['Telenor', 'Zong', 'Ufone', 'Jazz']:
                feat[f'operator_{op}'] = (group['operator'] == op).sum()
            
            feat['operator_diversity'] = group['operator'].nunique()
            
            # Geographic features
            feat['active_cells'] = group['cell_id'].nunique()
            feat['cell_density'] = feat['active_cells'] / max(1, feat['total_devices'])
            
            # Movement features
            if 'movement_score' in group.columns:
                feat['avg_movement'] = group['movement_score'].mean()
            else:
                feat['avg_movement'] = 0
            
            # Signal features
            if 'signal_strength' in group.columns:
                feat['avg_signal'] = group['signal_strength'].mean()
                feat['signal_variance'] = group['signal_strength'].std()
            else:
                feat['avg_signal'] = -75
                feat['signal_variance'] = 5
            
            # Temporal patterns (lag features)
            if len(features) > 0:
                last = features[-1]
                feat['device_growth'] = feat['total_devices'] - last.get('total_devices', 0)
                feat['detection_trend'] = feat['detection_rate'] - last.get('detection_rate', 0)
            else:
                feat['device_growth'] = 0
                feat['detection_trend'] = 0
            
            # Rolling averages (if enough history)
            if len(features) >= 5:
                last_5 = [f['total_devices'] for f in features[-5:]]
                feat['rolling_avg_5min'] = np.mean(last_5)
                feat['rolling_std_5min'] = np.std(last_5)
            else:
                feat['rolling_avg_5min'] = feat['total_devices']
                feat['rolling_std_5min'] = 0
            
            features.append(feat)
        
        return pd.DataFrame(features)
    
    def build_models(self, input_dim):
        """
        Build all sub-models in a unified architecture
        """
        print("\n📊 Building unified models...")
        
        # Shared input layer (transfer learning)
        shared_input = layers.Input(shape=(input_dim,))
        
        # Shared hidden layers (learn common patterns)
        shared_dense = layers.Dense(128, activation='relu', name='shared_dense_1')(shared_input)
        shared_dense = layers.Dropout(0.3)(shared_dense)
        shared_dense = layers.Dense(64, activation='relu', name='shared_dense_2')(shared_dense)
        shared_dense = layers.Dropout(0.2)(shared_dense)
        
        # ==========================================
        # TASK 1: Density Prediction (Regression)
        # ==========================================
        density_branch = layers.Dense(32, activation='relu')(shared_dense)
        density_output = layers.Dense(1, name='density_prediction')(density_branch)
        
        # ==========================================
        # TASK 2: Anomaly Detection (Binary)
        # ==========================================
        anomaly_branch = layers.Dense(32, activation='relu')(shared_dense)
        anomaly_output = layers.Dense(1, activation='sigmoid', name='anomaly_detection')(anomaly_branch)
        
        # ==========================================
        # TASK 3: Operator Forecast (Multi-class)
        # ==========================================
        operator_branch = layers.Dense(32, activation='relu')(shared_dense)
        operator_output = layers.Dense(4, activation='softmax', name='operator_forecast')(operator_branch)
        
        # ==========================================
        # TASK 4: Movement Prediction (Regression)
        # ==========================================
        movement_branch = layers.Dense(32, activation='relu')(shared_dense)
        movement_output = layers.Dense(1, name='movement_prediction')(movement_branch)
        
        # Create multi-output model
        self.unified_model = models.Model(
            inputs=shared_input,
            outputs=[density_output, anomaly_output, operator_output, movement_output]
        )
        
        # Compile with multiple losses
        self.unified_model.compile(
            optimizer='adam',
            loss={
                'density_prediction': 'mse',
                'anomaly_detection': 'binary_crossentropy',
                'operator_forecast': 'categorical_crossentropy',
                'movement_prediction': 'mse'
            },
            metrics={
                'density_prediction': ['mae'],
                'anomaly_detection': ['accuracy'],
                'operator_forecast': ['accuracy'],
                'movement_prediction': ['mae']
            }
        )
        
        print("✅ Unified model built successfully!")
        
        # Also train Isolation Forest for real-time anomaly detection
        self.anomaly_model = IsolationForest(contamination=0.1, random_state=42)
        
        return self.unified_model
    
    def prepare_training_data(self, df):
        """
        Prepare features and labels for all tasks
        """
        print("\n📊 Preparing training data...")
        
        # Extract features
        X = self.extract_features(df)
        
        if X.empty:
            print("❌ No data to train on")
            return None, None, None, None, None
        
        # Scale features
        X_scaled = self.feature_scaler.fit_transform(X)
        
        # Labels for each task
        y_density = X['total_devices'].values
        
        # Anomaly labels (using statistical outliers)
        threshold = X['total_devices'].quantile(0.95)
        y_anomaly = (X['total_devices'] > threshold).astype(int)
        
        # Operator labels (which operator will dominate next period)
        operator_cols = [c for c in X.columns if c.startswith('operator_')]
        y_operator = X[operator_cols].idxmax(axis=1).str.replace('operator_', '').values
        y_operator_encoded = self.operator_encoder.fit_transform(y_operator)
        y_operator_cat = tf.keras.utils.to_categorical(y_operator_encoded)
        
        # Movement labels (for prediction)
        y_movement = X['avg_movement'].shift(-1).fillna(0).values
        
        print(f"✅ Training data ready: {X.shape[0]} samples, {X.shape[1]} features")
        
        return X_scaled, y_density, y_anomaly, y_operator_cat, y_movement
    
    def train(self, df, epochs=50, batch_size=32):
        """
        Train the unified model on all tasks simultaneously
        """
        print("\n" + "="*70)
        print("🚀 TRAINING UNIFIED CROWD INTELLIGENCE MODEL")
        print("="*70)
        
        X, y_density, y_anomaly, y_operator, y_movement = self.prepare_training_data(df)
        
        if X is None:
            return
        
        # Build model
        self.build_models(X.shape[1])
        
        # Callbacks
        callbacks_list = [
            callbacks.EarlyStopping(patience=10, restore_best_weights=True),
            callbacks.ReduceLROnPlateau(factor=0.5, patience=5),
            callbacks.ModelCheckpoint(
                f"{self.model_dir}/unified_model.keras",
                save_best_only=True
            )
        ]
        
        # Train
        history = self.unified_model.fit(
            X, 
            {
                'density_prediction': y_density,
                'anomaly_detection': y_anomaly,
                'operator_forecast': y_operator,
                'movement_prediction': y_movement
            },
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            callbacks=callbacks_list,
            verbose=1
        )
        
        self.training_history = history.history
        print("\n✅ Training complete!")
        
        # Train Isolation Forest for real-time detection
        self.anomaly_model.fit(X)
        
        # Train clustering model
        self.cluster_model = DBSCAN(eps=0.5, min_samples=5)
        self.cluster_model.fit(X)
        
        # Save all models
        self.save_models()
        
        return history
    
    def predict(self, features):
        """
        Make predictions for all tasks simultaneously
        """
        if isinstance(features, dict):
            features = pd.DataFrame([features])
        
        # Scale features
        X = self.feature_scaler.transform(features)
        
        # Get predictions from unified model
        density_pred, anomaly_pred, operator_pred, movement_pred = self.unified_model.predict(X)
        
        # Get anomaly score from Isolation Forest
        anomaly_score = self.anomaly_model.decision_function(X)[0]
        is_anomaly = self.anomaly_model.predict(X)[0] == -1
        
        # Get cluster
        cluster = self.cluster_model.fit_predict(X)[0] if hasattr(self.cluster_model, 'labels_') else -1
        
        # Decode operator prediction
        operator_idx = np.argmax(operator_pred[0])
        operator = self.operator_encoder.inverse_transform([operator_idx])[0]
        
        return {
            'predicted_devices': int(density_pred[0][0]),
            'density_confidence': float(1 - anomaly_pred[0][0]),
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_score),
            'dominant_operator': operator,
            'operator_probabilities': {
                op: float(prob) for op, prob in zip(
                    self.operator_encoder.classes_, 
                    operator_pred[0]
                )
            },
            'movement_score': float(movement_pred[0][0]),
            'behavior_cluster': int(cluster)
        }
    
    def analyze_current_situation(self, current_data):
        """
        Comprehensive analysis of current crowd situation
        """
        features = self.extract_features(current_data)
        
        if features.empty:
            return {"error": "Insufficient data for analysis"}
        
        # Get latest features
        latest_features = features.iloc[-1:].copy()
        
        # Make predictions
        predictions = self.predict(latest_features)
        
        # Add real-time stats
        predictions.update({
            'current_devices': len(current_data['imsi'].unique()),
            'current_detections': len(current_data),
            'active_operators': current_data['operator'].unique().tolist(),
            'active_cells': current_data['cell_id'].nunique(),
            'timestamp': datetime.now().isoformat()
        })
        
        # Add recommendations
        predictions['recommendations'] = self.generate_recommendations(predictions)
        
        return predictions
    
    def generate_recommendations(self, predictions):
        """
        Generate actionable recommendations based on predictions
        """
        recommendations = []
        
        # Crowd density recommendation
        if predictions['predicted_devices'] > 100:
            recommendations.append("🔴 High crowd expected - Consider additional resources")
        elif predictions['predicted_devices'] > 50:
            recommendations.append("🟡 Moderate crowd - Normal operations sufficient")
        else:
            recommendations.append("🟢 Low crowd - Reduced resources needed")
        
        # Anomaly recommendation
        if predictions['is_anomaly']:
            recommendations.append("⚠️ ANOMALY DETECTED - Investigate unusual activity")
        
        # Operator recommendation
        if predictions['dominant_operator']:
            recommendations.append(f"📱 {predictions['dominant_operator']} users are dominant")
        
        # Movement recommendation
        if predictions['movement_score'] > 0.5:
            recommendations.append("🚶 High device movement detected - Crowd is mobile")
        
        return recommendations
    
    def save_models(self):
        """Save all models to disk"""
        # Save unified model
        self.unified_model.save(f"{self.model_dir}/unified_model.keras")
        
        # Save scaler and encoders
        joblib.dump(self.feature_scaler, f"{self.model_dir}/feature_scaler.pkl")
        joblib.dump(self.operator_encoder, f"{self.model_dir}/operator_encoder.pkl")
        joblib.dump(self.anomaly_model, f"{self.model_dir}/anomaly_model.pkl")
        
        # Save config
        config = {
            'training_history': self.training_history,
            'feature_columns': list(self.extract_features(pd.DataFrame()).columns)
        }
        with open(f"{self.model_dir}/model_config.json", 'w') as f:
            json.dump(config, f)
        
        print(f"💾 Models saved to {self.model_dir}/")
    
    def load_models(self):
        """Load saved models"""
        try:
            self.unified_model = models.load_model(f"{self.model_dir}/unified_model.keras")
            self.feature_scaler = joblib.load(f"{self.model_dir}/feature_scaler.pkl")
            self.operator_encoder = joblib.load(f"{self.model_dir}/operator_encoder.pkl")
            self.anomaly_model = joblib.load(f"{self.model_dir}/anomaly_model.pkl")
            print("✅ Models loaded successfully!")
            return True
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            return False

# ==========================================
# REAL-TIME INTEGRATION WITH YOUR IMSI CATCHER
# ==========================================

class CrowdIntelligenceIntegrator:
    """
    Integrates the unified model with your live IMSI data
    """
    
    def __init__(self):
        self.model = UnifiedCrowdIntelligence()
        self.data_buffer = []
        self.buffer_size = 100
        
        # Try to load existing model
        if not self.model.load_models():
            print("⚠️ No existing model found. Will train when enough data collected.")
    
    def process_imsi_data(self, df):
        """
        Process new IMSI data and generate intelligence
        """
        if df.empty:
            return None
        
        # Add to buffer
        self.data_buffer.extend(df.to_dict('records'))
        
        # Keep only recent data
        if len(self.data_buffer) > self.buffer_size:
            self.data_buffer = self.data_buffer[-self.buffer_size:]
        
        # Create DataFrame
        buffer_df = pd.DataFrame(self.data_buffer)
        
        # Train if enough data and no model
        if len(buffer_df) > 100 and not hasattr(self.model, 'unified_model'):
            print("📊 Training model on collected data...")
            self.model.train(buffer_df, epochs=30)
        
        # Analyze current situation
        if hasattr(self.model, 'unified_model'):
            return self.model.analyze_current_situation(buffer_df)
        
        return None

# ==========================================
# USAGE EXAMPLE
# ==========================================

def example_usage():
    """
    Example of how to use the unified model
    """
    
    # Sample IMSI data (replace with your actual data)
    sample_data = pd.DataFrame({
        'timestamp': pd.date_range('2026-04-03 10:00:00', periods=100, freq='T'),
        'imsi': [f'41006{i}' for i in range(100)],
        'operator': np.random.choice(['Telenor', 'Zong', 'Ufone', 'Jazz'], 100),
        'cell_id': np.random.randint(1, 10, 100),
        'signal_strength': np.random.randint(-90, -50, 100)
    })
    
    # Initialize integrator
    integrator = CrowdIntelligenceIntegrator()
    
    # Process data and get predictions
    result = integrator.process_imsi_data(sample_data)
    
    if result:
        print("\n" + "="*70)
        print("🎯 CROWD INTELLIGENCE REPORT")
        print("="*70)
        
        print(f"\n📊 CURRENT STATUS:")
        print(f"   Devices: {result.get('current_devices', 'N/A')}")
        print(f"   Active Operators: {result.get('active_operators', 'N/A')}")
        
        print(f"\n🔮 PREDICTIONS:")
        print(f"   Expected Devices: {result.get('predicted_devices', 'N/A')}")
        print(f"   Dominant Operator: {result.get('dominant_operator', 'N/A')}")
        print(f"   Anomaly Detected: {result.get('is_anomaly', 'N/A')}")
        
        print(f"\n📈 OPERATOR PROBABILITIES:")
        for op, prob in result.get('operator_probabilities', {}).items():
            print(f"   {op}: {prob:.1%}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in result.get('recommendations', []):
            print(f"   {rec}")
    
    return integrator

if __name__ == "__main__":
    # Run example
    integrator = example_usage()
    
    print("\n" + "="*70)
    print("🚀 Unified model ready for live IMSI data!")
    print("="*70)
