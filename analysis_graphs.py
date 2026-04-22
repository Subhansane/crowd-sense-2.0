#!/usr/bin/env python3
"""
IMSI Data Analysis & Visualization Dashboard
Creates professional graphs of your crowd data
"""

import requests
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.dates as mdates
from matplotlib.patches import Patch
import os
import time

# Configuration
API_URL = "http://192.168.18.38:5000"
OUTPUT_DIR = "analysis_reports"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

class IMSIAnalyzer:
    def __init__(self):
        self.colors = {
            'Telenor': '#800080',  # Purple
            'Zong': '#FF0000',      # Red
            'Ufone': '#FFD700',     # Gold
            'Jazz': '#0000FF',       # Blue
            'Unknown': '#808080'     # Gray
        }
        
    def fetch_data(self):
        """Fetch all data from API"""
        print("📡 Fetching data from proxy...")
        
        try:
            # Get stats
            stats = requests.get(f"{API_URL}/stats", timeout=5).json()
            
            # Get recent IMSIs
            recent = requests.get(f"{API_URL}/recent?limit=500", timeout=5).json()
            
            # Get operators
            operators = requests.get(f"{API_URL}/operators", timeout=5).json()
            
            print(f"✅ Fetched {len(recent.get('data', []))} records")
            return stats, recent, operators
            
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None, None, None
    
    def create_operator_pie_chart(self, operators, filename):
        """Create pie chart of operator distribution"""
        if not operators or 'operators' not in operators:
            return
        
        data = operators['operators']
        if not data:
            return
        
        # Prepare data
        labels = [item['operator'] for item in data]
        sizes = [item['count'] for item in data]
        colors = [self.colors.get(label, '#808080') for label in labels]
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Pie chart
        wedges, texts, autotexts = ax1.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        ax1.set_title('Operator Market Share', fontsize=16, weight='bold', pad=20)
        
        # Bar chart
        bars = ax2.bar(labels, sizes, color=colors, edgecolor='black', linewidth=1.5)
        ax2.set_title('Device Count by Operator', fontsize=16, weight='bold', pad=20)
        ax2.set_xlabel('Operator', fontsize=12)
        ax2.set_ylabel('Number of Devices', fontsize=12)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom', fontsize=11, weight='bold')
        
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/{filename}_operator_distribution.png", dpi=150, bbox_inches='tight')
        plt.show()
        print(f"✅ Saved operator graph to {OUTPUT_DIR}/{filename}_operator_distribution.png")
    
    def create_timeline_graph(self, recent_data, filename):
        """Create timeline of detections"""
        if not recent_data or 'data' not in recent_data:
            return
        
        data = recent_data['data']
        if len(data) < 2:
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Detections over time
        ax1.scatter(df['timestamp'], [1]*len(df), 
                   c=df['operator'].map(self.colors), 
                   alpha=0.6, s=50)
        ax1.set_yticks([])
        ax1.set_xlabel('Time', fontsize=12)
        ax1.set_title('IMSI Detections Over Time', fontsize=16, weight='bold', pad=20)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Add grid
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # Plot 2: Cumulative detections
        df['cumulative'] = range(1, len(df) + 1)
        ax2.plot(df['timestamp'], df['cumulative'], 
                linewidth=2, color='blue', marker='o', markersize=4)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.set_ylabel('Cumulative IMSIs', fontsize=12)
        ax2.set_title('Cumulative Detections', fontsize=16, weight='bold', pad=20)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/{filename}_timeline.png", dpi=150, bbox_inches='tight')
        plt.show()
        print(f"✅ Saved timeline graph to {OUTPUT_DIR}/{filename}_timeline.png")
    
    def create_heatmap(self, recent_data, filename):
        """Create hourly heatmap of activity"""
        if not recent_data or 'data' not in recent_data:
            return
        
        data = recent_data['data']
        if len(data) < 5:
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        
        # Create hour/minute matrix
        hours = range(24)
        heatmap_data = []
        
        for hour in hours:
            hour_data = df[df['hour'] == hour]
            heatmap_data.append(len(hour_data))
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Bar chart by hour
        bars = ax1.bar(hours, heatmap_data, color='darkblue', alpha=0.7)
        ax1.set_xlabel('Hour of Day', fontsize=12)
        ax1.set_ylabel('Number of Detections', fontsize=12)
        ax1.set_title('Activity by Hour', fontsize=16, weight='bold', pad=20)
        ax1.set_xticks(range(0, 24, 2))
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Operator breakdown by hour
        operator_hour = df.groupby(['hour', 'operator']).size().unstack(fill_value=0)
        
        if not operator_hour.empty:
            operator_hour.plot(kind='bar', stacked=True, ax=ax2, 
                              color=[self.colors.get(op, '#808080') for op in operator_hour.columns])
            ax2.set_xlabel('Hour of Day', fontsize=12)
            ax2.set_ylabel('Number of Detections', fontsize=12)
            ax2.set_title('Operator Activity by Hour', fontsize=16, weight='bold', pad=20)
            ax2.legend(title='Operator')
            ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/{filename}_heatmap.png", dpi=150, bbox_inches='tight')
        plt.show()
        print(f"✅ Saved heatmap to {OUTPUT_DIR}/{filename}_heatmap.png")
    
    def create_dashboard(self):
        """Create complete analysis dashboard"""
        print("\n" + "="*60)
        print("📊 GENERATING IMSI ANALYSIS DASHBOARD")
        print("="*60)
        
        # Fetch data
        stats, recent, operators = self.fetch_data()
        
        if not stats and not recent and not operators:
            print("❌ No data available")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate all graphs
        if operators:
            self.create_operator_pie_chart(operators, timestamp)
        
        if recent:
            self.create_timeline_graph(recent, timestamp)
            self.create_heatmap(recent, timestamp)
        
        # Print summary
        print("\n" + "="*60)
        print("📈 ANALYSIS SUMMARY")
        print("="*60)
        
        if stats:
            print(f"📱 Total Unique Devices: {stats.get('total_devices', 0)}")
        
        if operators and 'operators' in operators:
            print("\n📊 Operator Distribution:")
            for op in operators['operators']:
                print(f"   • {op['operator']}: {op['count']} devices")
        
        if recent and 'data' in recent:
            data = recent['data']
            print(f"\n🕐 Analysis Period: {len(data)} detections")
            if data:
                first = data[-1]['timestamp'][:19] if data else 'N/A'
                last = data[0]['timestamp'][:19] if data else 'N/A'
                print(f"   From: {first}")
                print(f"   To:   {last}")
        
        print(f"\n💾 Graphs saved to: {OUTPUT_DIR}/")
        print("="*60)

def continuous_monitoring():
    """Run continuous analysis every 5 minutes"""
    analyzer = IMSIAnalyzer()
    
    print("🔄 Continuous Analysis Mode - Press Ctrl+C to stop")
    print("Generating new report every 5 minutes...\n")
    
    counter = 1
    while True:
        print(f"\n📊 Report #{counter} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        analyzer.create_dashboard()
        
        counter += 1
        print("\n⏰ Waiting 5 minutes for next analysis...")
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    import sys
    
    print("""
    ╔════════════════════════════════════════════╗
    ║     IMSI DATA ANALYSIS & VISUALIZATION     ║
    ╚════════════════════════════════════════════╝
    """)
    
    print("Choose mode:")
    print("1. Generate single analysis report")
    print("2. Continuous monitoring (every 5 minutes)")
    print("3. View latest graphs")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    analyzer = IMSIAnalyzer()
    
    if choice == "1":
        analyzer.create_dashboard()
    elif choice == "2":
        continuous_monitoring()
    elif choice == "3":
        # Show latest graphs
        os.system(f"ls -la {OUTPUT_DIR}/ | tail -20")
        print(f"\n📁 Graphs saved in: {OUTPUT_DIR}/")
    else:
        print("Invalid choice")
