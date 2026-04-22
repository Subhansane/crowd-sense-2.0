#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import os
import re

class SimpleRadar:
    def __init__(self):
        self.devices = set()
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.suptitle("IMSI Radar - Live Detection", fontsize=14)
        
    def update(self, frame):
        if os.path.exists("imsi_output.txt"):
            with open("imsi_output.txt", "r") as f:
                content = f.read()
                imsis = re.findall(r'410 0[346] \d+', content)
                for imsi in imsis:
                    self.devices.add(imsi)
        self.ax.clear()
        operators = {'Telenor': 0, 'Ufone': 0, 'Zong': 0, 'Jazz': 0}
        for imsi in self.devices:
            if '410 06' in imsi:
                operators['Telenor'] += 1
            elif '410 03' in imsi:
                operators['Ufone'] += 1
            elif '410 04' in imsi:
                operators['Zong'] += 1
            elif '410 01' in imsi or '410 07' in imsi:
                operators['Jazz'] += 1
        bars = self.ax.bar(operators.keys(), operators.values(), color=['green', 'orange', 'red', 'blue'])
        self.ax.set_ylabel('Number of Devices')
        self.ax.set_title(f'Total Unique IMSIs: {len(self.devices)}')
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                self.ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom')
        return self.ax,
    
    def run(self):
        ani = animation.FuncAnimation(self.fig, self.update, interval=2000)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    radar = SimpleRadar()
    print("Simple Radar Starting...")
    radar.run()
