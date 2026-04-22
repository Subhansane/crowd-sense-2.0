#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import os
import re
import subprocess

class InferenceRadar:
    def __init__(self):
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(14, 6))
        self.fig.suptitle("Network Presence: IMSI vs. Signal Inference", fontsize=14)
        self.stats_file = os.path.expanduser("~/IMSI-catcher-master/crowd_stats.txt")

    def get_auto_hopper_stats(self):
        """Read the latest stats from the auto hopper's stats file."""
        zong_hits, jazz_hits, telenor_hits, ufone_hits = 0, 0, 0, 0
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    content = f.read()
                    # This is a simple parse; you might need to adjust based on your stats file format
                    zong_match = re.search(r'ZONG[^\d]*(\d+)', content, re.IGNORECASE)
                    jazz_match = re.search(r'JAZZ[^\d]*(\d+)', content, re.IGNORECASE)
                    telenor_match = re.search(r'TELENOR[^\d]*(\d+)', content, re.IGNORECASE)
                    ufone_match = re.search(r'UFONE[^\d]*(\d+)', content, re.IGNORECASE)
                    
                    if zong_match:
                        zong_hits = int(zong_match.group(1))
                    if jazz_match:
                        jazz_hits = int(jazz_match.group(1))
                    if telenor_match:
                        telenor_hits = int(telenor_match.group(1))
                    if ufone_match:
                        ufone_hits = int(ufone_match.group(1))
            except Exception as e:
                print(f"Error reading stats: {e}")
        return {'Zong': zong_hits, 'Jazz': jazz_hits, 'Telenor': telenor_hits, 'Ufone': ufone_hits}

    def get_imsi_counts(self):
        """Count IMSIs per operator from the main output file."""
        counts = {'Telenor': 0, 'Ufone': 0, 'Zong': 0, 'Jazz': 0}
        if os.path.exists("imsi_output.txt"):
            try:
                with open("imsi_output.txt", "r") as f:
                    content = f.read()
                    for operator in counts.keys():
                        # Simple count of how many lines contain the operator name
                        counts[operator] = len(re.findall(rf',\s*{operator},', content, re.IGNORECASE))
            except Exception as e:
                print(f"Error reading IMSI file: {e}")
        return counts

    def update(self, frame):
        imsi_counts = self.get_imsi_counts()
        signal_hits = self.get_auto_hopper_stats()

        # Clear axes
        self.ax1.clear()
        self.ax2.clear()

        # --- Plot 1: Confirmed IMSIs (What you KNOW) ---
        operators = list(imsi_counts.keys())
        imsi_values = list(imsi_counts.values())
        colors = ['purple', 'gold', 'red', 'blue']
        bars1 = self.ax1.bar(operators, imsi_values, color=colors)
        self.ax1.set_title('Confirmed Users (via IMSI)', fontweight='bold')
        self.ax1.set_ylabel('Unique IMSIs Captured')
        for bar, val in zip(bars1, imsi_values):
            if val > 0:
                self.ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                              f'{val}', ha='center', va='bottom')

        # --- Plot 2: Inferred Presence (Signal Hits from Auto Hopper) ---
        signal_values = [signal_hits[op] for op in operators]
        bars2 = self.ax2.bar(operators, signal_values, color=colors, alpha=0.6)
        self.ax2.set_title('Inferred Presence (Signal Hits)', fontweight='bold')
        self.ax2.set_ylabel('Signal Detections')
        for bar, val in zip(bars2, signal_values):
            if val > 0:
                self.ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                              f'{val}', ha='center', va='bottom')

        # Add a note about inference
        self.ax2.text(0.5, -0.15, 
                     "Note: High signal hits but low IMSI capture suggests 4G/5G-only networks.",
                     transform=self.ax2.transAxes, ha='center', fontsize=9, style='italic')

        return self.ax1, self.ax2

    def run(self):
        ani = animation.FuncAnimation(self.fig, self.update, interval=10000)  # Update every 10 seconds
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    radar = InferenceRadar()
    print("🚀 Inference Radar Started")
    print("   • Left chart: What your IMSI catcher CONFIRMS")
    print("   • Right chart: What your auto hopper INFERS (signal presence)")
    print("   A high right bar + low left bar = 4G/5G users in the crowd!")
    radar.run()
