#!/usr/bin/env python3
"""
Unified Timeline Analyzer - Shows both IMSI captures AND inferred signal hits
Tracks real network activity vs. signal presence over time
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import DateFormatter
import numpy as np
import time
import os
import re
import datetime
import json
from collections import defaultdict, deque
from pathlib import Path

class UnifiedTimeline:
    def __init__(self, history_minutes=60):
        self.history_minutes = history_minutes
        
        # Data storage for IMSI events (confirmed users)
        self.imsi_events = deque(maxlen=5000)
        
        # Data storage for signal hits (inferred presence)
        self.signal_hits = defaultdict(lambda: deque(maxlen=1000))
        
        # Stats files
        self.stats_file = "unified_traffic_stats.json"
        self.hopper_stats_file = os.path.expanduser("~/IMSI-catcher-master/crowd_stats.txt")
        
        # Network colors
        self.network_colors = {
            'Telenor': '#800080',  # Purple
            'Ufone': '#FFD700',    # Gold
            'Zong': '#FF0000',      # Red
            'Jazz': '#0000FF',      # Blue
            'Unknown': '#808080'    # Gray
        }
        
        # Setup the plot
        self.fig = plt.figure(figsize=(16, 12))
        self.fig.suptitle(f"Unified Network Timeline - IMSI vs Signal Inference (Last {history_minutes} Minutes)", 
                         fontsize=16, fontweight='bold')
        
        # Create subplots
        self.ax1 = self.fig.add_subplot(3, 2, 1)  # IMSI Timeline
        self.ax2 = self.fig.add_subplot(3, 2, 2)  # Signal Hits Timeline
        self.ax3 = self.fig.add_subplot(3, 2, 3)  # IMSI Network Breakdown
        self.ax4 = self.fig.add_subplot(3, 2, 4)  # Signal Network Breakdown
        self.ax5 = self.fig.add_subplot(3, 1, 3)  # Combined 24-Hour Pattern
        
        # Load previous stats
        self.load_stats()
        
        # Initialize file positions
        self.last_imsi_position = 0
        self.last_stats_mod_time = 0
        
    def load_stats(self):
        """Load previously saved statistics"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    print(f"📊 Loaded previous stats from {self.stats_file}")
            except Exception as e:
                print(f"Could not load stats: {e}")
    
    def parse_imsi_line(self, line):
        """Extract IMSI and operator from a log line"""
        # Look for operator names
        operator = 'Unknown'
        if 'Telenor' in line:
            operator = 'Telenor'
        elif 'Ufone' in line:
            operator = 'Ufone'
        elif 'Zong' in line:
            operator = 'Zong'
        elif 'Jazz' in line:
            operator = 'Jazz'
        
        # Extract IMSI
        imsi_match = re.search(r'410 0[3467] \d+', line)
        imsi = imsi_match.group(0) if imsi_match else None
        
        # Extract timestamp from line if present
        ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
        if ts_match:
            try:
                timestamp = datetime.datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S.%f').timestamp()
            except:
                timestamp = time.time()
        else:
            timestamp = time.time()
        
        return {
            'timestamp': timestamp,
            'operator': operator,
            'imsi': imsi,
            'type': 'imsi',
            'raw': line.strip()
        }
    
    def read_hopper_stats(self):
        """Read signal hits from auto hopper stats file"""
        hits = defaultdict(int)
        if os.path.exists(self.hopper_stats_file):
            try:
                # Check if file was modified
                mod_time = os.path.getmtime(self.hopper_stats_file)
                if mod_time > self.last_stats_mod_time:
                    with open(self.hopper_stats_file, 'r') as f:
                        content = f.read()
                        
                        # Extract hit counts for each network
                        for network in ['ZONG', 'JAZZ', 'TELENOR', 'UFONE']:
                            pattern = rf'{network}[^\d]*(\d+)'
                            match = re.search(pattern, content, re.IGNORECASE)
                            if match:
                                hits[network.capitalize()] = int(match.group(1))
                    
                    self.last_stats_mod_time = mod_time
                    
                    # Add signal hit events to timeline
                    current_time = time.time()
                    for network, count in hits.items():
                        if count > 0:
                            self.signal_hits[network].append({
                                'timestamp': current_time,
                                'count': count,
                                'network': network
                            })
            except Exception as e:
                print(f"Error reading hopper stats: {e}")
        
        return hits
    
    def read_new_ims_data(self):
        """Read new IMSI events from imsi_output.txt"""
        new_events = []
        if os.path.exists("imsi_output.txt"):
            try:
                stat = os.stat("imsi_output.txt")
                if stat.st_size > self.last_imsi_position:
                    with open("imsi_output.txt", 'r') as f:
                        f.seek(self.last_imsi_position)
                        lines = f.readlines()
                        self.last_imsi_position = f.tell()
                        
                        for line in lines:
                            if '410 0' in line:  # Contains IMSI data
                                event = self.parse_imsi_line(line)
                                if event['imsi']:
                                    new_events.append(event)
                                    self.imsi_events.append(event)
            except Exception as e:
                print(f"Error reading IMSI file: {e}")
        
        return new_events
    
    def update_plots(self, frame):
        """Update all plots with new data"""
        # Read new data
        new_ims_events = self.read_new_ims_data()
        signal_hits = self.read_hopper_stats()
        
        # Clear all axes
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        self.ax5.clear()
        
        now = time.time()
        time_window = now - (self.history_minutes * 60)
        
        # ==========================================
        # PLOT 1: IMSI Timeline (Confirmed Users)
        # ==========================================
        recent_ims = [e for e in self.imsi_events if e['timestamp'] >= time_window]
        
        if recent_ims:
            timestamps = [datetime.datetime.fromtimestamp(e['timestamp']) for e in recent_ims]
            operators = [e['operator'] for e in recent_ims]
            
            # Create scatter plot
            op_map = {op: i for i, op in enumerate(self.network_colors.keys())}
            y_values = [op_map.get(op, 4) for op in operators]
            
            self.ax1.scatter(timestamps, y_values, 
                           c=[self.network_colors.get(op, '#808080') for op in operators],
                           alpha=0.7, s=40, edgecolors='black', linewidth=0.5)
            
            self.ax1.set_yticks(list(op_map.values()))
            self.ax1.set_yticklabels(list(op_map.keys()))
            self.ax1.set_title(f'✅ Confirmed Users (IMSI Captures) - Total: {len(recent_ims)}', 
                             fontweight='bold', color='darkgreen')
            self.ax1.set_xlabel('Time')
            self.ax1.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            plt.setp(self.ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # ==========================================
        # PLOT 2: Signal Timeline (Inferred Presence)
        # ==========================================
        all_signals = []
        for network, hits in self.signal_hits.items():
            recent_hits = [h for h in hits if h['timestamp'] >= time_window]
            for hit in recent_hits:
                all_signals.append(hit)
        
        if all_signals:
            timestamps = [datetime.datetime.fromtimestamp(h['timestamp']) for h in all_signals]
            networks = [h['network'] for h in all_signals]
            sizes = [min(h['count'] * 10, 200) for h in all_signals]  # Scale dot size by hit count
            
            op_map = {op: i for i, op in enumerate(self.network_colors.keys())}
            y_values = [op_map.get(n, 4) for n in networks]
            
            scatter = self.ax2.scatter(timestamps, y_values, s=sizes,
                                      c=[self.network_colors.get(n, '#808080') for n in networks],
                                      alpha=0.5, edgecolors='black', linewidth=0.5)
            
            # Add size legend
            self.ax2.text(0.02, 0.98, 'Dot size = signal strength', 
                        transform=self.ax2.transAxes, fontsize=8,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            self.ax2.set_yticks(list(op_map.values()))
            self.ax2.set_yticklabels(list(op_map.keys()))
            self.ax2.set_title(f'📡 Inferred Presence (Signal Hits) - Networks: {len(set(networks))}', 
                             fontweight='bold', color='darkred')
            self.ax2.set_xlabel('Time')
            self.ax2.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            plt.setp(self.ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # ==========================================
        # PLOT 3: IMSI Network Breakdown
        # ==========================================
        imsi_counts = defaultdict(int)
        for e in recent_ims:
            imsi_counts[e['operator']] += 1
        
        if imsi_counts:
            networks = list(imsi_counts.keys())
            counts = list(imsi_counts.values())
            colors = [self.network_colors.get(n, '#808080') for n in networks]
            
            bars = self.ax3.bar(networks, counts, color=colors, alpha=0.8)
            self.ax3.set_title(f'IMSI Distribution - Total: {sum(counts)}', fontweight='bold')
            self.ax3.set_ylabel('Confirmed Users')
            for bar, count in zip(bars, counts):
                self.ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                            str(count), ha='center', va='bottom')
        
        # ==========================================
        # PLOT 4: Signal Network Breakdown
        # ==========================================
        signal_counts = defaultdict(int)
        for network, hits in self.signal_hits.items():
            recent = [h for h in hits if h['timestamp'] >= time_window]
            signal_counts[network] = len(recent)
        
        if signal_counts:
            networks = list(signal_counts.keys())
            counts = list(signal_counts.values())
            colors = [self.network_colors.get(n, '#808080') for n in networks]
            
            bars = self.ax4.bar(networks, counts, color=colors, alpha=0.6, hatch='//')
            self.ax4.set_title(f'Signal Distribution - Total: {sum(counts)} bursts', fontweight='bold')
            self.ax4.set_ylabel('Signal Detections')
            for bar, count in zip(bars, counts):
                self.ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                            str(count), ha='center', va='bottom')
        
        # ==========================================
        # PLOT 5: Combined 24-Hour Pattern
        # ==========================================
        hours = range(24)
        imsi_hourly = defaultdict(int)
        signal_hourly = defaultdict(int)
        
        # Aggregate IMSI data by hour
        for e in self.imsi_events:
            hour = datetime.datetime.fromtimestamp(e['timestamp']).hour
            imsi_hourly[hour] += 1
        
        # Aggregate signal data by hour
        for network, hits in self.signal_hits.items():
            for hit in hits:
                hour = datetime.datetime.fromtimestamp(hit['timestamp']).hour
                signal_hourly[hour] += hit['count']
        
        imsi_by_hour = [imsi_hourly.get(h, 0) for h in hours]
        signal_by_hour = [signal_hourly.get(h, 0) for h in hours]
        
        # Plot both on same graph
        width = 0.35
        x = np.arange(len(hours))
        
        bars1 = self.ax5.bar(x - width/2, imsi_by_hour, width, label='Confirmed IMSIs', 
                            color='green', alpha=0.7)
        bars2 = self.ax5.bar(x + width/2, signal_by_hour, width, label='Signal Hits (Inferred)', 
                            color='orange', alpha=0.5, hatch='//')
        
        self.ax5.set_title('24-Hour Pattern: IMSI vs Signal Inference', fontweight='bold')
        self.ax5.set_xlabel('Hour of Day')
        self.ax5.set_ylabel('Activity Count')
        self.ax5.set_xticks(x[::2])
        self.ax5.set_xticklabels([f'{h}:00' for h in hours[::2]])
        self.ax5.legend()
        
        # Find and highlight peak hours
        if max(imsi_by_hour) > 0:
            peak_imsi = hours[imsi_by_hour.index(max(imsi_by_hour))]
            self.ax5.axvline(x=peak_imsi - 0.35, color='green', linestyle='--', alpha=0.5, 
                           label=f'IMSI Peak: {peak_imsi}:00')
        if max(signal_by_hour) > 0:
            peak_signal = hours[signal_by_hour.index(max(signal_by_hour))]
            self.ax5.axvline(x=peak_signal + 0.35, color='orange', linestyle=':', alpha=0.5,
                           label=f'Signal Peak: {peak_signal}:00')
        
        # Add summary statistics
        total_ims = len(self.imsi_events)
        total_signals = sum(len(hits) for hits in self.signal_hits.values())
        
        summary = (f"📊 SUMMARY | Confirmed IMSIs: {total_ims} | Signal Bursts: {total_signals} | "
                  f"Networks: {len([n for n in self.network_colors.keys() if n != 'Unknown'])}")
        
        self.fig.text(0.5, 0.01, summary, ha='center', fontsize=11, fontweight='bold',
                     bbox=dict(boxstyle="round", facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        return self.ax1, self.ax2, self.ax3, self.ax4, self.ax5
    
    def run(self):
        """Run the unified timeline analyzer"""
        print("="*70)
        print("📊 UNIFIED TIMELINE ANALYZER - IMSI + INFERENCE")
        print("="*70)
        print("Tracking:")
        print("  • Top Left:     ✅ Confirmed IMSI captures (real users)")
        print("  • Top Right:    📡 Inferred signal hits (network presence)")
        print("  • Middle Left:  📊 IMSI network breakdown")
        print("  • Middle Right: 📊 Signal network breakdown")
        print("  • Bottom:       📈 24-hour pattern comparison")
        print("="*70)
        print("Press Ctrl+C to stop\n")
        
        # Initialize file positions
        if os.path.exists("imsi_output.txt"):
            self.last_imsi_position = os.path.getsize("imsi_output.txt")
        
        # Create animation
        ani = animation.FuncAnimation(self.fig, self.update_plots, interval=10000, cache_frame_data=False)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    analyzer = UnifiedTimeline(history_minutes=60)
    
    try:
        analyzer.run()
    except KeyboardInterrupt:
        print("\n\n👋 Unified Timeline Analyzer Stopped")
        print("📊 Data saved for future analysis")
