#!/usr/bin/env python3
"""
Run AI Analysis on Live IMSI Data
"""

import pandas as pd
import time
import os
import json
from datetime import datetime
import re
from unified_crowd_model import CrowdIntelligenceIntegrator

def load_imsi_data(filepath="imsi_output.txt", minutes_back=60):
    """Load IMSI data from your log file"""
    if not os.path.exists(filepath):
        print(f"⚠️ No data file found: {filepath}")
        return pd.DataFrame()
    
    data = []
    cutoff_time = datetime.now() - pd.Timedelta(minutes=minutes_back)
    
    with open(filepath, 'r') as f:
        for line in f:
            if '410' in line and not line.startswith('Nb'):
                # Parse IMSI line
                parts = [p.strip() for p in line.split(';')]
                
                if len(parts) >= 11:
                    # Extract data
                    imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
                    operator = "Unknown"
                    if "Telenor" in line:
                        operator = "Telenor"
                    elif "Zong" in line:
                        operator = "Zong"
                    elif "Ufone" in line:
                        operator = "Ufone"
                    elif "Jazz" in line:
                        operator = "Jazz"
                    
                    # Get timestamp
                    timestamp = parts[-1] if len(parts) > 0 else datetime.now().isoformat()
                    
                    data.append({
                        'timestamp': timestamp,
                        'imsi': imsi_match.group(0) if imsi_match else "",
                        'operator': operator,
                        'cell_id': parts[9] if len(parts) > 9 else "0",
                        'lac': parts[8] if len(parts) > 8 else "0"
                    })
    
    df = pd.DataFrame(data)
    print(f"📊 Loaded {len(df)} IMSI records from last {minutes_back} minutes")
    return df

def main():
    print("="*70)
    print("🧠 IMSI CROWD INTELLIGENCE AI - Linux Mint")
    print("="*70)
    
    # Initialize AI integrator
    integrator = CrowdIntelligenceIntegrator()
    
    # Load your IMSI data
    df = load_imsi_data()
    
    if df.empty:
        print("❌ No IMSI data found. Run your IMSI catcher first!")
        return
    
    # Process with AI
    result = integrator.process_imsi_data(df)
    
    if result:
        print("\n" + "="*70)
        print("🎯 AI CROWD INTELLIGENCE REPORT")
        print("="*70)
        
        print(f"\n📊 CURRENT STATUS:")
        print(f"   Total Devices: {result.get('current_devices', 'N/A')}")
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
        print(f"   Anomaly Score: {result.get('anomaly_score', 0):.2f}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in result.get('recommendations', []):
            print(f"   {rec}")
        
        # Save report
        report_file = f"ai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Report saved to: {report_file}")
    
    else:
        print("⏳ Not enough data for AI analysis yet.")
        print("   Continue running IMSI catcher to collect more data.")

if __name__ == "__main__":
    main()
