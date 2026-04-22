#!/usr/bin/env python3
"""
Real-Time Hybrid Monitor - Continuous prediction of unseen devices
"""

import os
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
from hybrid_predictor_patched import HybridUnseenDevicePredictor, HybridConfig  # FIXED IMPORT

class RealtimeHybridMonitor:
    def __init__(self):
        self.data_buffer = deque(maxlen=2000)
        self.last_position = 0
        
        print("="*60)
        print("🚀 REAL-TIME HYBRID MONITOR")
        print("="*60)
        
        self.model = HybridUnseenDevicePredictor(HybridConfig())
        if not self.model.load():
            print("❌ No trained model. Run train_hybrid_patched.py first")
            exit()
        
        print("✅ Model loaded")
        print("📡 Monitoring imsi_output.txt")
        print("="*60)
    
    def parse_line(self, line):
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
    
    def run(self):
        print("\n👀 Waiting for data...\n")
        
        while True:
            try:
                if os.path.exists("imsi_output.txt"):
                    with open("imsi_output.txt", "r") as f:
                        f.seek(self.last_position)
                        lines = f.readlines()
                        self.last_position = f.tell()
                        
                        for line in lines:
                            data = self.parse_line(line)
                            if data:
                                self.data_buffer.append(data)
                
                if len(self.data_buffer) > 50:
                    df = pd.DataFrame(list(self.data_buffer))
                    
                    # Spread timestamps over last hour
                    if len(df) > 0:
                        start = datetime.now() - timedelta(minutes=60)
                        df['timestamp'] = [start + timedelta(seconds=i*5) for i in range(len(df))]
                        df = df.sort_values('timestamp')
                    
                    result = self.model.predict_total(df)
                    
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                    print(f"   Observed: {result['observed_devices']}")
                    print(f"   → Estimated Total: ~{result['estimated_total_devices']}")
                    print(f"   → Unseen: +{result['estimated_unseen_devices']}")
                    print(f"   Multiplier: {result['hybrid_multiplier']}")
                    
                    if result.get('unseen_by_operator_estimate'):
                        print(f"   Unseen by operator:")
                        for op, count in result['unseen_by_operator_estimate'].items():
                            print(f"      {op}: ~{count}")
                
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n👋 Monitor stopped")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    monitor = RealtimeHybridMonitor()
    monitor.run()
