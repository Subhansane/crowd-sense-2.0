#!/usr/bin/env python3
"""
Real-Time BiLSTM Monitor - Continuously processes live IMSI data
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import signal
from unified_bilstm_model import UnifiedCrowdIntelligenceBiLSTM, ModelConfig

class RealtimeBiLSTMMonitor:
    def __init__(self):
        self.running = True
        self.data_buffer = deque(maxlen=2000)
        self.last_position = 0
        self.last_prediction_time = 0
        self.prediction_interval = 30  # Seconds between predictions
        
        # Load model
        print("="*70)
        print("🚀 REAL-TIME BILSTM MONITOR")
        print("="*70)
        
        config = ModelConfig()
        config.seq_len = 6
        config.model_dir = "ai_models"
        
        self.model = UnifiedCrowdIntelligenceBiLSTM(config)
        
        if not self.model.load_artifacts():
            print("❌ No trained model found. Training on collected data first...")
            self.need_training = True
        else:
            print("✅ Model loaded successfully")
            self.need_training = False
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        print(f"📡 Monitoring imsi_output.txt")
        print(f"⏱️  Prediction every {self.prediction_interval} seconds")
        print("="*70 + "\n")
    
    def shutdown(self, signum, frame):
        print("\n🛑 Shutting down monitor...")
        self.running = False
    
    def parse_imsi_line(self, line):
        """Parse IMSI line from file"""
        if '410' not in line or line.startswith('Nb'):
            return None
        
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
            return None
        
        return {
            'timestamp': datetime.now(),
            'imsi': line[:30],
            'operator': operator,
            'cell_id': 1,
            'signal_strength': -75,
            'movement_score': 0.5
        }
    
    def get_new_data(self):
        """Read new lines from imsi_output.txt"""
        if not os.path.exists("imsi_output.txt"):
            return []
        
        new_data = []
        with open("imsi_output.txt", "r") as f:
            f.seek(self.last_position)
            lines = f.readlines()
            self.last_position = f.tell()
            
            for line in lines:
                data = self.parse_imsi_line(line)
                if data:
                    new_data.append(data)
                    self.data_buffer.append(data)
        
        return new_data
    
    def get_dataframe(self):
        """Convert buffer to DataFrame with proper time distribution"""
        if len(self.data_buffer) < 50:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(self.data_buffer))
        
        # Spread timestamps over last hour for proper sequence
        if len(df) > 0:
            start_time = datetime.now() - timedelta(minutes=60)
            df['timestamp'] = [start_time + timedelta(seconds=i*5) for i in range(len(df))]
            df = df.sort_values('timestamp')
        
        return df
    
    def train_on_collected_data(self):
        """Train model on collected data"""
        if len(self.data_buffer) < 200:
            print(f"📊 Collecting more data... ({len(self.data_buffer)}/200)")
            return False
        
        print(f"\n📚 Training model on {len(self.data_buffer)} records...")
        df = self.get_dataframe()
        
        try:
            self.model.train(df)
            self.need_training = False
            print("✅ Training complete!")
            return True
        except Exception as e:
            print(f"❌ Training failed: {e}")
            return False
    
    def make_prediction(self):
        """Make and display prediction"""
        df = self.get_dataframe()
        
        if df.empty or len(df) < 50:
            print(f"⏳ Waiting for data... ({len(df)} records)")
            return
        
        result = self.model.predict_from_raw(df)
        
        if result and "error" not in result:
            # Clear previous line and print
            print("\n" + "="*70)
            print(f"🎯 REAL-TIME PREDICTION [{datetime.now().strftime('%H:%M:%S')}]")
            print("="*70)
            
            print(f"\n📊 Predicted Devices: {result.get('predicted_devices', 0)}")
            print(f"📱 Dominant Operator: {result.get('dominant_operator', 'N/A')}")
            print(f"⚠️ Anomaly: {result.get('anomaly_probability', 0):.1%}")
            print(f"🚶 Movement: {result.get('movement_score', 0):.2f}")
            
            print(f"\n📈 Operator Distribution:")
            for op, prob in result.get('operator_probabilities', {}).items():
                bar = "█" * int(prob * 40)
                print(f"   {op:10s}: {bar} {prob:.1%}")
            
            # Save to file
            with open("realtime_prediction.json", "w") as f:
                json.dump(result, f, indent=2)
        else:
            print(f"⚠️ Prediction error: {result}")
    
    def run(self):
        """Main monitoring loop"""
        print("👀 Waiting for IMSI data...\n")
        
        while self.running:
            try:
                # Get new data
                new_data = self.get_new_data()
                
                if new_data:
                    print(f"📊 +{len(new_data)} new IMSI records (Total: {len(self.data_buffer)})")
                
                # Train if needed and enough data
                if self.need_training and len(self.data_buffer) >= 200:
                    self.train_on_collected_data()
                
                # Make periodic predictions
                current_time = time.time()
                if not self.need_training and current_time - self.last_prediction_time >= self.prediction_interval:
                    if len(self.data_buffer) >= 50:
                        self.make_prediction()
                        self.last_prediction_time = current_time
                
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    monitor = RealtimeBiLSTMMonitor()
    monitor.run()
