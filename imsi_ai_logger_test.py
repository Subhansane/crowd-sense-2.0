#!/usr/bin/env python3
import os
import time
import csv
import datetime
from pathlib import Path

print("="*50)
print("AI LOGGER TEST VERSION - Guaranteed file creation")
print("="*50)

log_dir = "imsi_ai_data"
Path(log_dir).mkdir(parents=True, exist_ok=True)

counter = 0
while True:
    # Create a file every 30 seconds for testing
    timestamp = datetime.datetime.now()
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M%S")
    
    date_dir = os.path.join(log_dir, date_str)
    Path(date_dir).mkdir(exist_ok=True)
    
    # Create a test file
    test_file = os.path.join(date_dir, f"test_{time_str}.txt")
    with open(test_file, 'w') as f:
        f.write(f"Test file created at {timestamp}\n")
        f.write(f"This proves the AI logger can write files\n")
    
    print(f"[{timestamp.strftime('%H:%M:%S')}] ✅ Created: {test_file}")
    
    # Also check if imsi_output.txt exists and copy data
    if os.path.exists("imsi_output.txt"):
        size = os.path.getsize("imsi_output.txt")
        print(f"   imsi_output.txt size: {size} bytes")
        
        if size > 0:
            # Create a data file with actual IMSIs
            data_file = os.path.join(date_dir, f"imsi_{time_str}.csv")
            with open(data_file, 'w') as df:
                df.write("timestamp,imsi,operator,mcc,mnc\n")
                with open("imsi_output.txt", 'r') as source:
                    for line in source.readlines()[-10:]:  # Last 10 lines
                        if "410" in line:
                            df.write(f"{timestamp},{line.strip()}\n")
            print(f"   ✅ Data file created: {data_file}")
    
    counter += 1
    time.sleep(30)  # Create file every 30 seconds
