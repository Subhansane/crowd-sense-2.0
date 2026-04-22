#!/usr/bin/env python3
"""
Load ONLY your IMSI data CSV files (skip numpy test files)
"""

import pandas as pd
import os
import glob
import re
from datetime import datetime

def is_valid_imsi_csv(filepath):
    """Check if CSV contains actual IMSI data"""
    try:
        # Skip numpy test files
        if 'numpy' in filepath or 'tests/data' in filepath:
            return False
        
        # Skip files in ai_env directory
        if 'ai_env' in filepath:
            return False
        
        # Check file size (real IMSI files are usually > 1KB)
        if os.path.getsize(filepath) < 1000:
            return False
        
        # Peek at first few lines
        with open(filepath, 'r') as f:
            first_lines = f.read(2000)
            
            # Look for IMSI patterns
            if re.search(r'410\s+0[3467]\s+\d+', first_lines):
                return True
            
            # Look for IMSI column headers
            if 'imsi' in first_lines.lower() or 'IMSI' in first_lines:
                return True
        
        return False
    except:
        return False

def find_imsi_csv_files():
    """Find only your IMSI data CSV files"""
    imsi_files = []
    
    # Look in your project directory (not in ai_env)
    search_dirs = [
        ".",
        "imsi_ai_data",
        "imsi_ai_data/*/",
        "analysis_reports",
        "data"
    ]
    
    for search_dir in search_dirs:
        pattern = f"{search_dir}/*.csv"
        for filepath in glob.glob(pattern, recursive=True):
            if is_valid_imsi_csv(filepath):
                imsi_files.append(filepath)
                print(f"✅ Found IMSI CSV: {filepath}")
    
    return imsi_files

def load_imsi_data(filepath):
    """Load IMSI data from CSV"""
    print(f"\n📁 Loading: {filepath}")
    
    try:
        df = pd.read_csv(filepath)
        
        # Check if it has IMSI data
        has_imsi = False
        
        # Check column names
        for col in ['imsi', 'IMSI', 'imsi_number', 'IMSI_number']:
            if col in df.columns:
                has_imsi = True
                break
        
        # Check content for IMSI pattern
        if not has_imsi:
            for col in df.columns:
                if df[col].dtype == 'object':
                    sample = df[col].astype(str).head(10)
                    if sample.str.contains(r'410\s+0[3467]\s+\d+').any():
                        has_imsi = True
                        break
        
        if has_imsi:
            print(f"   ✅ {len(df)} records loaded")
            return df
        else:
            print(f"   ⚠️ No IMSI data found in this file")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def create_demo_data():
    """Create demo IMSI data for testing"""
    print("\n📊 Creating demo IMSI data...")
    
    import numpy as np
    
    np.random.seed(42)
    n_samples = 200
    
    # Generate timestamps
    timestamps = pd.date_range(
        start=datetime.now() - pd.Timedelta(hours=2),
        periods=n_samples,
        freq='30s'
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
            'cell_id': np.random.randint(1, 10),
            'lac': np.random.choice([359, 58803, 12345])
        })
    
    df = pd.DataFrame(data)
    print(f"   ✅ Created {len(df)} demo IMSI records")
    return df

def main():
    print("="*70)
    print("📊 IMSI CSV Loader - Find Your Data Files")
    print("="*70)
    
    # Find IMSI CSV files
    imsi_files = find_imsi_csv_files()
    
    if imsi_files:
        print(f"\n📂 Found {len(imsi_files)} IMSI CSV files")
        
        for filepath in imsi_files[:5]:  # Load first 5
            df = load_imsi_data(filepath)
            if df is not None:
                print(f"\n   📊 Data preview:")
                print(df[['timestamp', 'imsi', 'operator']].head())
    else:
        print("\n⚠️ No IMSI CSV files found.")
        print("   Creating demo data for testing...")
        df = create_demo_data()
        
        # Save demo data
        df.to_csv('demo_imsi_data.csv', index=False)
        print(f"\n   💾 Saved demo data to: demo_imsi_data.csv")
        print(f"   📊 Demo data preview:")
        print(df[['timestamp', 'imsi', 'operator']].head())

if __name__ == "__main__":
    main()
