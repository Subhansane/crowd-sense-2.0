#!/usr/bin/env python3
"""
Complete Integration: IMSI Catcher + Unified AI Model
Real-time crowd intelligence system
"""

import numpy as np
import pandas as pd
import re
import time
import os
import json
from datetime import datetime, timedelta
from collections import deque
import subprocess
import signal
import sys

# Import the upgraded model
from unified_crowd_model_upgraded import UnifiedCrowdIntelligence, CrowdIntelligenceIntegrator

# ==========================================
# IMSI DATA COLLECTOR
# ==========================================

class IMSIDataCollector:
    """Collects and processes IMSI data from imsi_output.txt"""
    
    def __init__(self, filepath="imsi_output.txt"):
        self.filepath = filepath
        self.last_position = 0
        self.data_buffer = deque(maxlen=10000)
        
    def get_new_data(self):
        """Read new IMSI lines from file"""
        if not os.path.exists(self.filepath):
            return []
        
        new_data = []
        with open(self.filepath, 'r') as f:
            f.seek(self.last_position)
            lines = f.readlines()
            self.last_position = f.tell()
            
            for line in lines:
                if '410' in line and not line.startswith('Nb'):
                    data = self.parse_imsi_line(line)
                    if data:
                        new_data.append(data)
                        self.data_buffer.append(data)
        
        return new_data
    
    def parse_imsi_line(self, line):
        """Parse IMSI line into structured data"""
        # Extract IMSI
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi_parts = imsi_match.group(0).split()
        
        # Determine operator
        operator = "Unknown"
        if "Telenor" in line:
            operator = "Telenor"
        elif "Zong" in line:
            operator = "Zong"
        elif "Ufone" in line:
            operator = "Ufone"
        elif "Jazz" in line:
            operator = "Jazz"
        
        # Extract cell info
        parts = [p.strip() for p in line.split(';')]
        cell_id = parts[9] if len(parts) > 9 else "1"
        lac = parts[8] if len(parts) > 8 else "359"
        
        return {
            'timestamp': datetime.now(),
            'imsi': imsi_match.group(0),
            'operator': operator,
            'cell_id': int(cell_id) if cell_id.isdigit() else 1,
            'lac': int(lac) if lac.isdigit() else 359,
            'signal_strength': -75  # Default value
        }
    
    def get_dataframe(self):
        """Get all buffered data as DataFrame"""
        if not self.data_buffer:
            return pd.DataFrame()
        return pd.DataFrame(list(self.data_buffer))

# ==========================================
# REAL-TIME AI MONITOR
# ==========================================

class RealtimeAIMonitor:
    """Monitors IMSI data and runs AI predictions in real-time"""
    
    def __init__(self):
        self.collector = IMSIDataCollector()
        self.ai = UnifiedCrowdIntelligence()
        self.running = True
        self.prediction_history = deque(maxlen=100)
        
        # Try to load existing model
        if not self.ai.load_models():
            print("⚠️ No existing AI model. Will train when enough data collected.")
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
    def shutdown(self, signum, frame):
        print("\n🛑 Shutting down AI Monitor...")
        self.running = False
    
    def train_if_needed(self, df):
        """Train model if we have enough data and no model exists"""
        if len(df) > 200 and not hasattr(self.ai, 'unified_model'):
            print(f"\n📚 Training AI on {len(df)} IMSI records...")
            self.ai.train(df, epochs=20)
            return True
        return False
    
    def run(self):
        """Main monitoring loop"""
        print("\n" + "="*70)
        print("🚀 REAL-TIME IMSI AI MONITOR")
        print("="*70)
        print("📡 Monitoring imsi_output.txt for new data...")
        print("🤖 AI will analyze crowd patterns in real-time\n")
        
        last_prediction_time = 0
        prediction_interval = 30  # Seconds between predictions
        
        while self.running:
            try:
                # Get new data
                new_data = self.collector.get_new_data()
                
                if new_data:
                    print(f"📊 Received {len(new_data)} new IMSI records")
                    
                    # Get full dataframe
                    df = self.collector.get_dataframe()
                    
                    # Train if needed
                    self.train_if_needed(df)
                    
                    # Make periodic predictions
                    current_time = time.time()
                    if current_time - last_prediction_time >= prediction_interval and hasattr(self.ai, 'unified_model'):
                        self.make_prediction(df)
                        last_prediction_time = current_time
                
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(5)
    
    def make_prediction(self, df):
        """Make and display AI predictions"""
        if df.empty or len(df) < 50:
            return
        
        try:
            result = self.ai.analyze_current_situation(df)
            
            if result and 'error' not in result:
                self.prediction_history.append(result)
                
                # Clear line and print prediction
                print("\n" + "="*70)
                print(f"🎯 AI PREDICTION - {datetime.now().strftime('%H:%M:%S')}")
                print("="*70)
                
                print(f"\n📊 CURRENT STATUS:")
                print(f"   Devices: {result.get('current_devices', 0)}")
                print(f"   Active Operators: {', '.join(result.get('active_operators', []))}")
                
                print(f"\n🔮 FORECAST:")
                print(f"   Expected Devices (next period): {result.get('predicted_devices', 0)}")
                print(f"   Dominant Operator: {result.get('dominant_operator', 'N/A')}")
                print(f"   Confidence: {result.get('density_confidence', 0):.1%}")
                
                print(f"\n📈 OPERATOR BREAKDOWN:")
                for op, prob in result.get('operator_probabilities', {}).items():
                    bar = "█" * int(prob * 40)
                    print(f"   {op:10s}: {bar} {prob:.1%}")
                
                print(f"\n⚠️ ALERTS:")
                if result.get('is_anomaly'):
                    print(f"   🔴 ANOMALY DETECTED - Unusual crowd pattern")
                if result.get('movement_score', 0) > 0.5:
                    print(f"   🚶 High device movement detected")
                
                print(f"\n💡 RECOMMENDATIONS:")
                for rec in result.get('recommendations', []):
                    print(f"   {rec}")
                
                # Save prediction to file
                self.save_prediction(result)
                
        except Exception as e:
            print(f"❌ Prediction error: {e}")
    
    def save_prediction(self, result):
        """Save prediction to JSON file"""
        try:
            filename = f"predictions/prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs("predictions", exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
        except:
            pass

# ==========================================
# DASHBOARD GENERATOR
# ==========================================

class DashboardGenerator:
    """Generates HTML dashboard from AI predictions"""
    
    @staticmethod
    def generate(predictions):
        """Create HTML dashboard"""
        if not predictions:
            return
        
        latest = predictions[-1]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>IMSI Crowd Intelligence Dashboard</title>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: auto; }}
                .card {{ background: #2a2a2a; border-radius: 10px; padding: 20px; margin: 10px; border-left: 4px solid #00ff00; }}
                .stat {{ font-size: 36px; font-weight: bold; color: #00ff00; }}
                .operator-bar {{ background: #333; border-radius: 5px; margin: 5px 0; overflow: hidden; }}
                .bar {{ padding: 5px 10px; color: white; }}
                .telenor {{ background: #800080; }}
                .zong {{ background: #ff4444; }}
                .ufone {{ background: #ffaa00; }}
                .jazz {{ background: #4444ff; }}
                .anomaly {{ color: #ff4444; animation: blink 1s infinite; }}
                @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📡 IMSI Crowd Intelligence Dashboard</h1>
                <p>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="grid">
                    <div class="card">
                        <h3>📊 Current Crowd</h3>
                        <div class="stat">{latest.get('current_devices', 0)}</div>
                        <div>Active Devices</div>
                    </div>
                    
                    <div class="card">
                        <h3>🔮 Prediction</h3>
                        <div class="stat">{latest.get('predicted_devices', 0)}</div>
                        <div>Expected Devices (Next Period)</div>
                    </div>
                    
                    <div class="card">
                        <h3>📱 Dominant Operator</h3>
                        <div class="stat">{latest.get('dominant_operator', 'N/A')}</div>
                        <div>Market Leader</div>
                    </div>
                    
                    <div class="card">
                        <h3>⚠️ Status</h3>
                        <div class="stat {'anomaly' if latest.get('is_anomaly') else ''}">
                            {'ANOMALY' if latest.get('is_anomaly') else 'NORMAL'}
                        </div>
                        <div>Detection Status</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📈 Operator Distribution Forecast</h3>
        """
        
        for op, prob in latest.get('operator_probabilities', {}).items():
            pct = prob * 100
            color = op.lower()
            html += f"""
                    <div class="operator-bar">
                        <div class="bar {color}" style="width: {pct}%;">{op}: {pct:.1f}%</div>
                    </div>
            """
        
        html += """
                </div>
                
                <div class="card">
                    <h3>💡 Recommendations</h3>
                    <ul>
        """
        
        for rec in latest.get('recommendations', []):
            html += f"<li>{rec}</li>\n"
        
        html += """
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("dashboard.html", "w") as f:
            f.write(html)
        print("📊 Dashboard updated: dashboard.html")

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    print("="*70)
    print("🚀 INTEGRATED IMSI CATCHER + AI SYSTEM")
    print("="*70)
    print("\nThis system combines:")
    print("  1. IMSI Data Collection")
    print("  2. Real-time AI Predictions")
    print("  3. Live Dashboard")
    print("  4. Anomaly Detection")
    print("\nMake sure your IMSI catcher is running!")
    print("="*70)
    
    # Start AI Monitor
    monitor = RealtimeAIMonitor()
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n\n👋 System stopped")
        
        # Generate final dashboard
        if monitor.prediction_history:
            DashboardGenerator.generate(monitor.prediction_history)
            print("📊 Final dashboard saved to dashboard.html")

if __name__ == "__main__":
    main()
