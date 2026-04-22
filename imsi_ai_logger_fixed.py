#!/usr/bin/env python3
"""
FIXED AI LOGGER - Creates real CSV files with IMSI data
Use this instead of the test version
"""

import os
import time
import csv
import datetime
from pathlib import Path
import re

class IMSILogger:
    def __init__(self, log_dir="imsi_ai_data", interval_minutes=2):
        self.log_dir = log_dir
        self.interval_seconds = interval_minutes * 60
        self.last_position = 0
        self.running = True
        self.seen_ims = set()
        
        # Create directory structure
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        self.today_dir = os.path.join(self.log_dir, datetime.datetime.now().strftime("%Y%m%d"))
        Path(self.today_dir).mkdir(exist_ok=True)
        
        print("="*60)
        print("FIXED AI LOGGER - CSV FILE GENERATOR")
        print("="*60)
        print(f"📁 Log directory: {os.path.abspath(self.log_dir)}")
        print(f"📁 Today's folder: {self.today_dir}")
        print(f"⏱️  Creating CSV files every {interval_minutes} minutes")
        print("="*60)
        
    def get_new_ims_data(self):
        """Read new IMSI data from imsi_output.txt"""
        new_data = []
        
        if not os.path.exists("imsi_output.txt"):
            return new_data
            
        try:
            with open("imsi_output.txt", "r") as f:
                f.seek(self.last_position)
                lines = f.readlines()
                self.last_position = f.tell()
                
                for line in lines:
                    # Look for IMSI patterns (410 06, 410 04, 410 03, 410 01)
                    match = re.search(r'410\s+0[3467]\s+\d+', line)
                    if match:
                        imsi = match.group(0)
                        
                        # Determine operator
                        operator = "Unknown"
                        if "410 06" in imsi:
                            operator = "Telenor"
                        elif "410 04" in imsi:
                            operator = "Zong"
                        elif "410 03" in imsi:
                            operator = "Ufone"
                        elif "410 01" in imsi or "410 07" in imsi:
                            operator = "Jazz"
                        
                        # Extract timestamp if available
                        timestamp = datetime.datetime.now().isoformat()
                        time_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
                        if time_match:
                            timestamp = time_match.group(0)
                        
                        # Only add if not seen before in this batch
                        if imsi not in self.seen_ims:
                            self.seen_ims.add(imsi)
                            new_data.append({
                                'timestamp': timestamp,
                                'imsi': imsi,
                                'operator': operator,
                                'mcc': '410',
                                'mnc': imsi.split()[1] if len(imsi.split()) > 1 else '00',
                                'full_line': line.strip()
                            })
        except Exception as e:
            print(f"Error reading file: {e}")
            
        return new_data
    
    def save_csv(self, data, filename):
        """Save data to CSV file"""
        if not data:
            return False
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['timestamp', 'imsi', 'operator', 'mcc', 'mnc'])
                # Write data
                for item in data:
                    writer.writerow([
                        item['timestamp'],
                        item['imsi'],
                        item['operator'],
                        item['mcc'],
                        item['mnc']
                    ])
            return True
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False
    
    def save_json(self, data, filename):
        """Optional: Save as JSON too"""
        import json
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'total_devices': len(data),
                    'devices': data
                }, f, indent=2)
            return True
        except:
            return False
    
    def run(self):
        """Main loop"""
        print("\n📊 Monitoring for IMSI data...")
        print("   (Press Ctrl+C to stop)\n")
        
        next_save = time.time() + self.interval_seconds
        current_batch = []
        
        try:
            while self.running:
                # Check for new data
                new_data = self.get_new_ims_data()
                if new_data:
                    current_batch.extend(new_data)
                    print(f"  ➕ {len(new_data)} new IMSIs (Total in batch: {len(current_batch)})")
                
                # Save if it's time
                if time.time() >= next_save and current_batch:
                    # Generate filename with timestamp
                    timestamp = datetime.datetime.now()
                    date_str = timestamp.strftime("%Y%m%d")
                    time_str = timestamp.strftime("%H%M%S")
                    
                    # Ensure today's directory exists
                    today_dir = os.path.join(self.log_dir, date_str)
                    Path(today_dir).mkdir(exist_ok=True)
                    
                    # Save CSV
                    csv_file = os.path.join(today_dir, f"imsi_{date_str}_{time_str}.csv")
                    if self.save_csv(current_batch, csv_file):
                        print(f"\n✅ Saved {len(current_batch)} IMSIs to: {csv_file}")
                        
                        # Show summary
                        operators = {}
                        for item in current_batch:
                            op = item['operator']
                            operators[op] = operators.get(op, 0) + 1
                        
                        print(f"   Summary: {operators}")
                    
                    # Optional: Save JSON too
                    json_file = os.path.join(today_dir, f"imsi_{date_str}_{time_str}.json")
                    self.save_json(current_batch, json_file)
                    
                    # Reset for next batch
                    current_batch = []
                    next_save = time.time() + self.interval_seconds
                    print("")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping AI Logger...")
            
            # Save any remaining data
            if current_batch:
                timestamp = datetime.datetime.now()
                date_str = timestamp.strftime("%Y%m%d")
                time_str = timestamp.strftime("%H%M%S")
                today_dir = os.path.join(self.log_dir, date_str)
                Path(today_dir).mkdir(exist_ok=True)
                
                csv_file = os.path.join(today_dir, f"imsi_{date_str}_{time_str}_final.csv")
                if self.save_csv(current_batch, csv_file):
                    print(f"✅ Saved final {len(current_batch)} IMSIs to: {csv_file}")
            
            print("👋 Goodbye!")

if __name__ == "__main__":
    logger = IMSILogger(interval_minutes=2)
    logger.run()
