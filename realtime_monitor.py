#!/usr/bin/env python3
"""
Real-Time IMSI Data Monitor
Shows IMSI data live as it's being uploaded to cloud
"""

import requests
import time
import os
import sys
from datetime import datetime
import json
from collections import deque

# Configuration
API_URL = "http://subhanscode.xo.je/imsi_api.php"
REFRESH_INTERVAL = 3  # seconds
MAX_HISTORY = 20  # Number of recent records to show

class IMSIRealtimeMonitor:
    def __init__(self):
        self.last_id = 0
        self.total_seen = 0
        self.stats = {
            'Telenor': 0,
            'Zong': 0,
            'Ufone': 0,
            'Jazz': 0,
            'Unknown': 0
        }
        self.recent_history = deque(maxlen=MAX_HISTORY)
        self.start_time = datetime.now()
        
    def fetch_latest_data(self):
        """Fetch most recent IMSI data from API"""
        try:
            response = requests.get(f"{API_URL}?action=recent&limit=50", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data', [])
        except Exception as e:
            print(f"⚠️ Connection error: {e}")
        return []
    
    def process_new_records(self, records):
        """Process and display new records"""
        new_records = [r for r in records if r.get('id', 0) > self.last_id]
        
        for record in sorted(new_records, key=lambda x: x['id']):
            self.last_id = max(self.last_id, record['id'])
            self.total_seen += 1
            
            # Update stats
            operator = record.get('operator', 'Unknown')
            if operator in self.stats:
                self.stats[operator] += 1
            else:
                self.stats['Unknown'] += 1
            
            # Add to history
            self.recent_history.append(record)
            
            # Display immediately
            self.display_record(record)
        
        return len(new_records)
    
    def display_record(self, record):
        """Display a single record with formatting"""
        timestamp = record.get('timestamp', '')[:19]  # Trim to seconds
        operator = record.get('operator', 'Unknown')
        imsi = record.get('imsi', '')
        imsi_short = imsi[-8:] if len(imsi) > 8 else imsi
        
        # Color codes for different operators
        colors = {
            'Telenor': '\033[95m',  # Purple
            'Zong': '\033[91m',      # Red
            'Ufone': '\033[93m',     # Yellow
            'Jazz': '\033[94m',      # Blue
            'Unknown': '\033[90m'    # Gray
        }
        reset = '\033[0m'
        
        color = colors.get(operator, '\033[90m')
        print(f"{color}📱 [{self.total_seen}] {timestamp} - {operator}: ...{imsi_short}{reset}")
    
    def display_header(self):
        """Display header with statistics"""
        os.system('clear')  # Clear screen for better viewing
        runtime = datetime.now() - self.start_time
        runtime_str = str(runtime).split('.')[0]  # Remove microseconds
        
        print("="*80)
        print("📡 REAL-TIME IMSI MONITOR")
        print("="*80)
        print(f"🕐 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Runtime: {runtime_str}")
        print(f"📊 Total IMSIs: {self.total_seen}")
        print(f"🔢 Last ID: {self.last_id}")
        print("-"*80)
        
        # Display current stats
        active_ops = {k: v for k, v in self.stats.items() if v > 0}
        if active_ops:
            print("📈 Current Stats:")
            for op, count in active_ops.items():
                pct = (count / self.total_seen * 100) if self.total_seen > 0 else 0
                print(f"   {op}: {count} ({pct:.1f}%)")
        print("="*80)
    
    def display_recent(self):
        """Display recent history"""
        if self.recent_history:
            print("\n🕐 Recent Detections:")
            for record in list(self.recent_history)[-5:]:
                ts = record.get('timestamp', '')[:19]
                op = record.get('operator', 'Unknown')
                imsi = record.get('imsi', '')[-8:]
                print(f"   {ts} - {op}: ...{imsi}")
    
    def run(self):
        """Main monitoring loop"""
        print("🚀 Starting real-time monitor...")
        time.sleep(1)
        
        try:
            while True:
                # Fetch latest data
                records = self.fetch_latest_data()
                
                # Process new records
                new_count = self.process_new_records(records)
                
                # Update display periodically
                if new_count > 0 or int(time.time()) % 10 == 0:
                    self.display_header()
                    self.display_recent()
                
                # Wait before next fetch
                time.sleep(REFRESH_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")
            print(f"📊 Final count: {self.total_seen} IMSIs")
            print(f"⏱️  Total runtime: {datetime.now() - self.start_time}")

class SimpleMonitor:
    """Simpler version - just shows new IMSIs as they arrive"""
    def run(self):
        print("="*60)
        print("📡 SIMPLE IMSI MONITOR")
        print("="*60)
        print("Waiting for new IMSI data...\n")
        
        last_id = 0
        total = 0
        
        try:
            while True:
                try:
                    response = requests.get(f"{API_URL}?action=recent&limit=20", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            records = data.get('data', [])
                            
                            for record in records:
                                if record.get('id', 0) > last_id:
                                    last_id = record['id']
                                    total += 1
                                    
                                    timestamp = record.get('timestamp', '')[:19]
                                    operator = record.get('operator', 'Unknown')
                                    imsi = record.get('imsi', '')[-8:]
                                    
                                    print(f"[{timestamp}] {operator}: ...{imsi}")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print(f"\n\n📊 Total IMSIs seen: {total}")

if __name__ == "__main__":
    # Choose which version to run
    print("\nChoose monitor type:")
    print("1. Full monitor (with stats and history)")
    print("2. Simple monitor (just new IMSIs)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        monitor = IMSIRealtimeMonitor()
        monitor.run()
    else:
        monitor = SimpleMonitor()
        monitor.run()
