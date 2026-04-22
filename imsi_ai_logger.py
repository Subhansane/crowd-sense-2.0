#!/usr/bin/env python3
import os
import sys
import time
import json
import csv
import datetime
import threading
from pathlib import Path
from collections import defaultdict
import signal

class IMSIAILogger:
    def __init__(self, log_dir="imsi_ai_data", interval_minutes=2):
        self.log_dir = log_dir
        self.interval_seconds = interval_minutes * 60
        self.current_imsidata = []
        self.running = True
        self.lock = threading.Lock()
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        print(f"IMSI AI Logger Started")
        print(f"Log directory: {os.path.abspath(self.log_dir)}")
        print(f"Creating new file every {interval_minutes} minutes")
        
    def shutdown(self, signum=None, frame=None):
        print("\nStopping IMSI Logger...")
        self.running = False
        
    def parse_imsi_line(self, line):
        try:
            if not line or line.startswith('Nb IMSI') or line.startswith('---'):
                return None
            parts = [p.strip() for p in line.split(';')]
            if len(parts) >= 11:
                imsi_data = {
                    'index': parts[0],
                    'tmsi1': parts[1] if parts[1] else None,
                    'tmsi2': parts[2] if parts[2] else None,
                    'imsi': parts[3] if len(parts) > 3 else None,
                    'country': parts[4] if len(parts) > 4 else None,
                    'brand': parts[5] if len(parts) > 5 else None,
                    'operator': parts[6] if len(parts) > 6 else None,
                    'mcc': parts[7] if len(parts) > 7 else None,
                    'mnc': parts[8] if len(parts) > 8 else None,
                    'lac': parts[9] if len(parts) > 9 else None,
                    'cellid': parts[10] if len(parts) > 10 else None,
                    'timestamp': parts[11] if len(parts) > 11 else None,
                    'capture_time': datetime.datetime.now().isoformat()
                }
                return imsi_data
        except Exception as e:
            print(f"Error parsing line: {e}")
        return None
    
    def save_current_data(self):
        if not self.current_imsidata:
            print("No IMSI data to save in this interval")
            return
        timestamp = datetime.datetime.now()
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        date_dir = os.path.join(self.log_dir, date_str)
        Path(date_dir).mkdir(exist_ok=True)
        base_filename = f"imsi_{date_str}_{time_str}"
        csv_file = os.path.join(date_dir, f"{base_filename}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if self.current_imsidata:
                writer = csv.DictWriter(f, fieldnames=self.current_imsidata[0].keys())
                writer.writeheader()
                writer.writerows(self.current_imsidata)
        json_file = os.path.join(date_dir, f"{base_filename}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'capture_start': self.current_imsidata[0]['capture_time'],
                    'capture_end': timestamp.isoformat(),
                    'total_devices': len(self.current_imsidata),
                    'interval_minutes': self.interval_seconds / 60
                },
                'devices': self.current_imsidata
            }, f, indent=2)
        simple_file = os.path.join(date_dir, f"{base_filename}_simple.txt")
        with open(simple_file, 'w', encoding='utf-8') as f:
            for device in self.current_imsidata:
                if device['imsi']:
                    f.write(f"{device['imsi']},{device['brand']},{device['mcc']},{device['mnc']},{device['timestamp']}\n")
        print(f"Saved {len(self.current_imsidata)} IMSIs to {date_dir}")
        
    def monitor_imsi_output(self):
        imsi_output_file = "imsi_output.txt"
        if not os.path.exists(imsi_output_file):
            Path(imsi_output_file).touch()
        print(f"Monitoring {imsi_output_file} for IMSI data...")
        with open(imsi_output_file, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            while self.running:
                line = f.readline()
                if line:
                    imsi_data = self.parse_imsi_line(line)
                    if imsi_data and imsi_data['imsi']:
                        with self.lock:
                            existing_ims = [d['imsi'] for d in self.current_imsidata if d['imsi']]
                            if imsi_data['imsi'] not in existing_ims:
                                self.current_imsidata.append(imsi_data)
                                print(f"New IMSI: {imsi_data['imsi'][:15]}... ({len(self.current_imsidata)} total)")
                else:
                    time.sleep(0.1)
    
    def timer_thread(self):
        while self.running:
            time.sleep(self.interval_seconds)
            with self.lock:
                if self.current_imsidata:
                    self.save_current_data()
                    self.current_imsidata = []
    
    def run(self):
        timer = threading.Thread(target=self.timer_thread)
        timer.daemon = True
        timer.start()
        self.monitor_imsi_output()

def main():
    logger = IMSIAILogger(log_dir="imsi_ai_data", interval_minutes=2)
    try:
        logger.run()
    except KeyboardInterrupt:
        if logger.current_imsidata:
            logger.save_current_data()
        print("Goodbye!")

if __name__ == "__main__":
    main()
