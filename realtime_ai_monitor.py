#!/usr/bin/env python3
import time
import pandas as pd
import re
from datetime import datetime
from simple_ai_model import SimpleCrowdAI

ai = SimpleCrowdAI()
ai.load()

while True:
    # Load latest 100 records
    data = []
    with open("imsi_output.txt", "r") as f:
        lines = f.readlines()[-100:]
    
    for line in lines:
        if '410' in line:
            data.append({'timestamp': datetime.now(), 'imsi': line[:20], 'operator': 'Telenor', 'cell_id': 1})
    
    if data:
        df = pd.DataFrame(data)
        result = ai.predict(df)
        if result:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Predicted: {result['predicted_devices']} devices | Anomaly: {result['is_anomaly']}")
    time.sleep(60)
