#!/usr/bin/env python3
"""
Run AI Analysis on YOUR IMSI CSV Data
"""

import pandas as pd
import numpy as np
import os
import glob
import json
from datetime import datetime
import re

# Import the unified model
from unified_crowd_model import UnifiedCrowdIntelligence

def load_my_imsi_data():
    """Load your actual IMSI data"""
    
    # Try different sources
    
    # 1. Try imsi_output.txt
    if os.path.exists("imsi_output.txt"):
        print("\n📁 Reading from imsi_output.txt...")
        data = []
        with open("imsi_output.txt", 'r') as f:
            for line in f:
                if '410' in line and not line.startswith('Nb'):
                    imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
                    if imsi_match:
                        operator = "Unknown"
                        if "Telenor" in line:
                            operator = "Telenor"
                        elif "Zong" in line:
                            operator = "Zong"
                        elif "Ufone" in line:
                            operator = "Ufone"
                        elif "Jazz" in line:
                            operator = "Jazz"
                        
                        data.append({
                            'timestamp': datetime.now(),
                            'imsi': imsi_match.group(0),
                            'operator': operator,
                            'cell_id': np.random.randint(1, 10),
                            'lac': 359
                        })
        
        if data:
            df = pd.DataFrame(data)
            print(f"   ✅ Loaded {len(df)} records from imsi_output.txt")
            return df
    
    # 2. Try demo data
    if os.path.exists("demo_imsi_data.csv"):
        print("\n📁 Reading from demo_imsi_data.csv...")
        df = pd.read_csv("demo_imsi_data.csv")
        print(f"   ✅ Loaded {len(df)} records")
        return df
    
    # 3. Create fresh data
    print("\n📊 Creating fresh sample data...")
    np.random.seed(42)
    n_samples = 300
    
    timestamps = pd.date_range(
        start=datetime.now() - pd.Timedelta(hours=2),
        periods=n_samples,
        freq='24s'
    )
    
    data = []
    operators = ['Telenor', 'Zong', 'Ufone', 'Jazz']
    weights = [0.60, 0.25, 0.10, 0.05]
    
    for ts in timestamps:
        op = np.random.choice(operators, p=weights)
        if op == 'Telenor':
            imsi = f"41006{np.random.randint(100000000, 999999999)}"
        elif op == 'Zong':
            imsi = f"41004{np.random.randint(100000000, 999999999)}"
        elif op == 'Ufone':
            imsi = f"41003{np.random.randint(100000000, 999999999)}"
        else:
            imsi = f"41001{np.random.randint(100000000, 999999999)}"
        
        data.append({
            'timestamp': ts,
            'imsi': imsi,
            'operator': op,
            'cell_id': np.random.randint(1, 8),
            'lac': np.random.choice([359, 58803, 12345])
        })
    
    df = pd.DataFrame(data)
    print(f"   ✅ Created {len(df)} records")
    return df

def main():
    print("="*70)
    print("🧠 AI ANALYSIS ON MY IMSI DATA")
    print("="*70)
    
    # Load your data
    df = load_my_imsi_data()
    
    if df is None or df.empty:
        print("❌ No data available")
        return
    
    print(f"\n📊 DATA SUMMARY:")
    print(f"   Total Records: {len(df)}")
    print(f"   Unique Devices: {df['imsi'].nunique()}")
    print(f"   Operators: {df['operator'].unique().tolist()}")
    
    # Initialize AI
    print("\n🤖 Initializing AI Model...")
    ai = UnifiedCrowdIntelligence()
    
    # Train the model
    print("\n📚 Training AI on your data...")
    history = ai.train(df, epochs=30)
    
    if history:
        print("✅ Training complete!")
        
        # Analyze current situation
        print("\n🔍 Analyzing current crowd situation...")
        result = ai.analyze_current_situation(df)
        
        if result:
            print("\n" + "="*70)
            print("🎯 AI ANALYSIS RESULTS")
            print("="*70)
            
            print(f"\n📊 CURRENT STATUS:")
            print(f"   Total Devices: {result.get('current_devices', 'N/A')}")
            print(f"   Unique IMSIs: {df['imsi'].nunique()}")
            print(f"   Active Operators: {', '.join(result.get('active_operators', []))}")
            
            print(f"\n🔮 PREDICTIONS:")
            print(f"   Expected Devices (next hour): {result.get('predicted_devices', 'N/A')}")
            print(f"   Confidence: {result.get('density_confidence', 0):.1%}")
            print(f"   Dominant Operator: {result.get('dominant_operator', 'N/A')}")
            print(f"   Movement Score: {result.get('movement_score', 0):.2f}")
            
            print(f"\n📈 OPERATOR PROBABILITIES:")
            for op, prob in result.get('operator_probabilities', {}).items():
                bar = "█" * int(prob * 50)
                print(f"   {op:10s}: {bar} {prob:.1%}")
            
            print(f"\n⚠️ ANOMALY DETECTION:")
            print(f"   Is Anomaly: {'⚠️ YES' if result.get('is_anomaly') else '✅ NO'}")
            
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in result.get('recommendations', []):
                print(f"   {rec}")
            
            # Save report
            report_file = f"ai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n💾 Report saved to: {report_file}")
        else:
            print("❌ Analysis failed")
    else:
        print("❌ Training failed")

if __name__ == "__main__":
    main()
