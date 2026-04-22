#!/usr/bin/env python3
"""
Network Traffic Timeline Analyzer
Tracks IMSI detections over time to identify peak hours and traffic patterns
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

class TimelineAnalyzer:
    def __init__(self, history_minutes=60):
        self.history_minutes = history_minutes
        self.max_history = history_minutes * 60  # Convert to seconds
        
        # Data storage
        self.timeline_data = deque(maxlen=10000)  # Store events with timestamps
        self.hourly_stats = defaultdict(int)
        self.daily_stats = defaultdict(lambda: defaultdict(int))
        
        # For real-time tracking
        self.last_save_time = time.time()
        self.stats_file = "traffic_stats.json"
        
        # Setup the plot
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle(f"Network Traffic Timeline - Last {history_minutes} Minutes", fontsize=16)
        
        # Create subplots
        self.ax1 = self.fig.add_subplot(3, 1, 1)  # Real-time activity
        self.ax2 = self.fig.add_subplot(3, 1, 2)  # Network breakdown
        self.ax3 = self.fig.add_subplot(3, 1, 3)  # Hourly pattern
        
        # Colors for networks
        self.network_colors = {
            'Telenor': '#800080',  # Purple
            'Ufone': '#FFD700',    # Gold
            'Zong': '#FF0000',      # Red
            'Jazz': '#0000FF',      # Blue
            'Unknown': '#808080'    # Gray
        }
        
        # Load previous stats if they exist
        self.load_stats()
        
    def load_stats(self):
        """Load previously saved statistics"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to integers for hourly_stats
                    for hour, count in data.get('hourly_stats', {}).items():
                        self.hourly_stats[int(hour)] = count
                    print(f"📊 Loaded previous stats from {self.stats_file}")
            except Exception as e:
                print(f"Could not load stats: {e}")
    
    def save_stats(self):
        """Save statistics for long-term analysis"""
        data = {
            'hourly_stats': dict(self.hourly_stats),
            'last_update': datetime.datetime.now().isoformat()
        }
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
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
        
        # Extract IMSI if present
        imsi_match = re.search(r'410 0[3467] \d+', line)
        imsi = imsi_match.group(0) if imsi_match else None
        
        return {
            'timestamp': time.time(),
            'operator': operator,
            'imsi': imsi,
            'raw': line.strip()
        }
    
    def read_new_data(self):
        """Read new entries from imsi_output.txt"""
        new_events = []
        if os.path.exists("imsi_output.txt"):
            try:
                # Get file size and read only new content
                stat = os.stat("imsi_output.txt")
                if not hasattr(self, 'last_position'):
                    self.last_position = stat.st_size
                    return new_events
                
                if stat.st_size > self.last_position:
                    with open("imsi_output.txt", 'r') as f:
                        f.seek(self.last_position)
                        lines = f.readlines()
                        self.last_position = f.tell()
                        
                        for line in lines:
                            event = self.parse_imsi_line(line)
                            if event['imsi']:  # Only count events with IMSI
                                new_events.append(event)
                                self.timeline_data.append(event)
                                
                                # Update hourly stats
                                hour = datetime.datetime.now().hour
                                self.hourly_stats[hour] += 1
                                
                                # Update daily stats
                                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                                self.daily_stats[date_str][event['operator']] += 1
            except Exception as e:
                print(f"Error reading file: {e}")
        
        return new_events
    
    def get_activity_by_minute(self, minutes=10):
        """Group activity into minute buckets for the last N minutes"""
        now = time.time()
        minute_buckets = defaultdict(lambda: defaultdict(int))
        
        for event in self.timeline_data:
            if now - event['timestamp'] <= self.history_minutes * 60:
                minute_key = int((now - event['timestamp']) / 60)  # Minutes ago
                if minute_key <= minutes:
                    minute_buckets[minute_key][event['operator']] += 1
        
        return minute_buckets
    
    def update_plot(self, frame):
        """Update all three plots"""
        # Read new data
        new_events = self.read_new_data()
        
        # Save stats every 5 minutes
        if time.time() - self.last_save_time > 300:  # 5 minutes
            self.save_stats()
            self.last_save_time = time.time()
        
        # Clear all axes
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        
        # ==========================================
        # PLOT 1: Real-time activity (last 10 minutes)
        # ==========================================
        now = time.time()
        recent_events = [e for e in self.timeline_data if now - e['timestamp'] <= 600]  # Last 10 minutes
        
        if recent_events:
            # Create time-based scatter plot
            timestamps = [datetime.datetime.fromtimestamp(e['timestamp']) for e in recent_events]
            operators = [e['operator'] for e in recent_events]
            
            # Create a numeric mapping for operators
            op_map = {op: i for i, op in enumerate(self.network_colors.keys())}
            y_values = [op_map.get(op, 4) for op in operators]  # 4 is index for Unknown
            
            # Scatter plot
            scatter = self.ax1.scatter(timestamps, y_values, 
                                      c=[self.network_colors.get(op, '#808080') for op in operators],
                                      alpha=0.6, s=30)
            
            # Formatting
            self.ax1.set_yticks(list(op_map.values()))
            self.ax1.set_yticklabels(list(op_map.keys()))
            self.ax1.set_xlabel('Time')
            self.ax1.set_ylabel('Network')
            self.ax1.set_title('Real-time Network Activity (Last 10 Minutes)')
            self.ax1.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            plt.setp(self.ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # ==========================================
        # PLOT 2: Network breakdown (last hour)
        # ==========================================
        hour_events = [e for e in self.timeline_data if now - e['timestamp'] <= 3600]  # Last hour
        network_counts = defaultdict(int)
        for e in hour_events:
            network_counts[e['operator']] += 1
        
        if network_counts:
            networks = list(network_counts.keys())
            counts = list(network_counts.values())
            colors = [self.network_colors.get(n, '#808080') for n in networks]
            
            bars = self.ax2.bar(networks, counts, color=colors)
            self.ax2.set_title(f'Network Distribution (Last Hour) - Total: {sum(counts)} IMSIs')
            self.ax2.set_ylabel('Number of IMSIs')
            
            # Add count labels on bars
            for bar, count in zip(bars, counts):
                self.ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                            str(count), ha='center', va='bottom')
        
        # ==========================================
        # PLOT 3: Hourly pattern (peak time detection)
        # ==========================================
        hours = range(24)
        hourly_counts = [self.hourly_stats.get(h, 0) for h in hours]
        
        if sum(hourly_counts) > 0:
            bars = self.ax3.bar(hours, hourly_counts, color='green', alpha=0.7)
            self.ax3.set_title('24-Hour Traffic Pattern (Historical)')
            self.ax3.set_xlabel('Hour of Day')
            self.ax3.set_ylabel('IMSI Count')
            self.ax3.set_xticks(range(0, 24, 2))
            
            # Highlight peak hours
            if max(hourly_counts) > 0:
                peak_hour = hours[hourly_counts.index(max(hourly_counts))]
                self.ax3.axvline(x=peak_hour, color='red', linestyle='--', alpha=0.5, 
                                label=f'Peak: {peak_hour}:00 ({max(hourly_counts)} IMSIs)')
                self.ax3.legend()
        
        # Add summary statistics as text
        total_ims = len([e for e in self.timeline_data if e['imsi']])
        recent_count = len(hour_events)
        
        summary = f"Total IMSIs Captured: {total_ims} | Last Hour: {recent_count} | Networks: {len(network_counts)}"
        self.fig.text(0.5, 0.01, summary, ha='center', fontsize=10, 
                     bbox=dict(boxstyle="round", facecolor='lightyellow'))
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        return self.ax1, self.ax2, self.ax3
    
    def run(self):
        """Run the timeline analyzer"""
        print("="*60)
        print("📊 NETWORK TRAFFIC TIMELINE ANALYZER")
        print("="*60)
        print("Tracking:")
        print("  • Real-time activity (last 10 minutes)")
        print("  • Network distribution (last hour)")
        print("  • 24-hour traffic patterns")
        print("  • Peak time detection")
        print("="*60)
        print("Press Ctrl+C to stop and save statistics")
        print("")
        
        # Initialize file position
        if os.path.exists("imsi_output.txt"):
            self.last_position = os.path.getsize("imsi_output.txt")
        else:
            self.last_position = 0
        
        # Create animation
        ani = animation.FuncAnimation(self.fig, self.update_plot, interval=5000)  # Update every 5 seconds
        plt.tight_layout()
        plt.show()
        
        # Save stats on exit
        self.save_stats()
        print(f"\n📁 Statistics saved to {self.stats_file}")

if __name__ == "__main__":
    analyzer = TimelineAnalyzer(history_minutes=60)
    
    try:
        analyzer.run()
    except KeyboardInterrupt:
        print("\n\n👋 Timeline Analyzer Stopped")
        print(f"📊 Final statistics saved for analysis")
