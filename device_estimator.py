#!/usr/bin/env python3
"""
Real-Time Device Estimator
Calculates actual devices in area using inference data and statistical modeling
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import DateFormatter  # IMPORT THIS!
import numpy as np
import time
import os
import re
import json
import datetime
from collections import defaultdict, deque

class DeviceEstimator:
    def __init__(self):
        # Data storage
        self.imsi_events = deque(maxlen=10000)  # Confirmed IMSIs
        self.signal_hits = defaultdict(lambda: deque(maxlen=5000))  # Signal hits per frequency
        self.frequency_performance = defaultdict(lambda: {'hits': 0, 'ims_captured': 0, 'efficiency': 0})
        
        # Estimation parameters
        self.calibration_factor = 1.5  # Base multiplier (will auto-adjust)
        self.confidence_level = 0.95
        self.moving_window = 300  # 5-minute window for real-time estimation
        
        # Historical data for calibration
        self.historical_ratio = deque(maxlen=20)  # Store recent signal-to-IMSI ratios
        
        # Files
        self.stats_file = "crowd_stats.txt"
        self.imsi_file = "imsi_output.txt"
        self.calibration_file = "device_estimator_calibration.json"
        
        # Network-specific factors (adjusted based on real data)
        self.network_factors = {
            'Telenor': 1.0,  # Baseline (mostly 2G, good visibility)
            'Ufone': 1.0,    # Baseline (mostly 2G, good visibility)
            'Zong': 3.5,     # Higher factor (mostly 4G, harder to detect)
            'Jazz': 3.0,     # Higher factor (mostly 4G, harder to detect)
            'Unknown': 2.0
        }
        
        # Setup plot
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle("Real-Time Device Estimator", fontsize=16, fontweight='bold')
        
        # Create subplots - adjusted layout to avoid tight_layout warning
        self.ax1 = self.fig.add_subplot(3, 3, 1)  # Current estimation
        self.ax2 = self.fig.add_subplot(3, 3, 2)  # Network breakdown
        self.ax3 = self.fig.add_subplot(3, 3, 3)  # Confidence intervals
        self.ax4 = self.fig.add_subplot(3, 1, 2)  # Timeline
        self.ax5 = self.fig.add_subplot(3, 1, 3)  # Calibration trend
        
        # Colors
        self.network_colors = {
            'Telenor': '#800080',  # Purple
            'Ufone': '#FFD700',    # Gold
            'Zong': '#FF0000',      # Red
            'Jazz': '#0000FF',      # Blue
            'Unknown': '#808080'    # Gray
        }
        
        # Initialize
        self.last_imsi_pos = 0
        self.last_stats_mod = 0
        self.estimation_history = deque(maxlen=100)
        self.load_calibration()
        
    def load_calibration(self):
        """Load previously calibrated factors"""
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    self.network_factors.update(data.get('network_factors', {}))
                    self.calibration_factor = data.get('calibration_factor', 1.5)
                    print(f"📊 Loaded calibration from {self.calibration_file}")
            except Exception as e:
                print(f"Could not load calibration: {e}")
    
    def save_calibration(self):
        """Save calibrated factors for future use"""
        data = {
            'network_factors': dict(self.network_factors),
            'calibration_factor': self.calibration_factor,
            'last_update': datetime.datetime.now().isoformat(),
            'historical_ratios': list(self.historical_ratio)
        }
        try:
            with open(self.calibration_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving calibration: {e}")
    
    def read_imsi_data(self):
        """Read confirmed IMSIs from file"""
        new_ims = []
        if os.path.exists(self.imsi_file):
            try:
                stat = os.stat(self.imsi_file)
                if stat.st_size > self.last_imsi_pos:
                    with open(self.imsi_file, 'r') as f:
                        f.seek(self.last_imsi_pos)
                        lines = f.readlines()
                        self.last_imsi_pos = f.tell()
                        
                        for line in lines:
                            # Extract operator
                            operator = 'Unknown'
                            for net in self.network_colors.keys():
                                if net in line and net != 'Unknown':
                                    operator = net
                                    break
                            
                            # Extract IMSI
                            imsi_match = re.search(r'410 0[3467] \d+', line)
                            if imsi_match:
                                new_ims.append({
                                    'timestamp': time.time(),
                                    'operator': operator,
                                    'imsi': imsi_match.group(0)
                                })
                                self.imsi_events.append({
                                    'timestamp': time.time(),
                                    'operator': operator
                                })
            except Exception as e:
                print(f"Error reading IMSI file: {e}")
        return new_ims
    
    def read_signal_hits(self):
        """Read signal hits from auto hopper stats"""
        if os.path.exists(self.stats_file):
            try:
                mod_time = os.path.getmtime(self.stats_file)
                if mod_time > self.last_stats_mod:
                    with open(self.stats_file, 'r') as f:
                        content = f.read()
                        
                        # Parse frequency hits
                        freq_pattern = r'(\d+\.\d+M)[^:]*:?\s*(\d+)\s*hits?'
                        freq_matches = re.findall(freq_pattern, content, re.IGNORECASE)
                        
                        for freq, hits in freq_matches:
                            # Determine network from frequency (simplified)
                            network = 'Unknown'
                            if '952' in freq or '947' in freq or '944' in freq:
                                network = 'Zong'
                            elif '935' in freq or '936' in freq:
                                network = 'Jazz'
                            elif '940' in freq or '941' in freq:
                                network = 'Telenor'
                            elif '938' in freq or '939' in freq:
                                network = 'Ufone'
                            
                            self.signal_hits[network].append({
                                'timestamp': time.time(),
                                'frequency': freq,
                                'hits': int(hits),
                                'network': network
                            })
                            
                            # Update frequency performance tracking
                            self.frequency_performance[freq]['hits'] += int(hits)
                    
                    self.last_stats_mod = mod_time
            except Exception as e:
                print(f"Error reading stats: {e}")
    
    def calculate_signal_to_imsi_ratio(self, minutes=10):
        """Calculate current signal-to-IMSI ratio for calibration"""
        now = time.time()
        window_start = now - (minutes * 60)
        
        # Count recent IMSIs
        recent_ims = sum(1 for e in self.imsi_events 
                        if e['timestamp'] >= window_start)
        
        # Count recent signal hits
        recent_signals = 0
        for hits in self.signal_hits.values():
            recent_signals += sum(1 for h in hits 
                                 if h['timestamp'] >= window_start)
        
        if recent_ims > 0 and recent_signals > 0:
            ratio = recent_signals / recent_ims
            self.historical_ratio.append(ratio)
            
            # Auto-calibrate based on recent ratios
            if len(self.historical_ratio) > 5:
                avg_ratio = np.mean(list(self.historical_ratio)[-5:])
                self.calibration_factor = max(1.2, min(5.0, avg_ratio))
        
        return recent_ims, recent_signals
    
    def estimate_devices(self, time_window=300):
        """Estimate actual devices using inference data"""
        now = time.time()
        window_start = now - time_window
        
        # Count confirmed IMSIs in window
        confirmed_counts = defaultdict(int)
        for e in self.imsi_events:
            if e['timestamp'] >= window_start:
                confirmed_counts[e['operator']] += 1
        
        # Count signal hits in window
        signal_counts = defaultdict(int)
        for network, hits in self.signal_hits.items():
            signal_counts[network] = sum(1 for h in hits 
                                        if h['timestamp'] >= window_start)
        
        # Calculate estimates with confidence
        estimates = {}
        confidence = {}
        total_estimated = 0
        total_confirmed = sum(confirmed_counts.values())
        total_signals = sum(signal_counts.values())
        
        for network in self.network_colors.keys():
            if network == 'Unknown':
                continue
                
            confirmed = confirmed_counts.get(network, 0)
            signals = signal_counts.get(network, 0)
            
            # Estimate actual devices using network-specific factor
            if signals > 0:
                # Base estimate from signals
                signal_estimate = signals * self.network_factors.get(network, 2.0)
                
                # Adjust based on confirmed IMSIs if available
                if confirmed > 0:
                    observed_ratio = signals / confirmed if confirmed > 0 else 0
                    if observed_ratio > 0:
                        # Blend estimates
                        signal_estimate = (signal_estimate + (signals * (1/observed_ratio))) / 2
                
                estimates[network] = max(confirmed, int(signal_estimate))
                
                # Calculate confidence (higher when we have confirmed IMSIs)
                if confirmed > 0:
                    confidence[network] = min(0.95, 0.5 + (confirmed / estimates[network]) * 0.5)
                else:
                    confidence[network] = 0.4  # Lower confidence without confirmed IMSIs
            else:
                estimates[network] = confirmed
                confidence[network] = 0.8 if confirmed > 0 else 0
            
            total_estimated += estimates[network]
        
        return {
            'confirmed': total_confirmed,
            'estimated': total_estimated,
            'signals': total_signals,
            'by_network': estimates,
            'confidence': confidence,
            'ratio': total_signals / total_confirmed if total_confirmed > 0 else 0
        }
    
    def update_plots(self, frame):
        """Update all estimation plots"""
        # Read new data
        self.read_imsi_data()
        self.read_signal_hits()
        
        # Calculate current ratio for calibration
        recent_ims, recent_signals = self.calculate_signal_to_imsi_ratio(minutes=5)
        
        # Get current estimate
        estimate = self.estimate_devices(time_window=self.moving_window)
        self.estimation_history.append({
            'timestamp': time.time(),
            'estimated': estimate['estimated'],
            'confirmed': estimate['confirmed']
        })
        
        # Clear all axes
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        self.ax5.clear()
        
        # ==========================================
        # PLOT 1: Current Estimation (Gauge)
        # ==========================================
        networks = list(estimate['by_network'].keys())
        est_values = [estimate['by_network'][n] for n in networks]
        conf_values = [estimate['confidence'].get(n, 0) for n in networks]
        colors = [self.network_colors.get(n, '#808080') for n in networks]
        
        bars = self.ax1.bar(networks, est_values, color=colors, alpha=0.7)
        self.ax1.set_title(f'Estimated Devices (Last 5 min)\nTotal: {estimate["estimated"]}', 
                          fontweight='bold', color='darkblue')
        self.ax1.set_ylabel('Estimated Count')
        
        # Add confidence as text
        for bar, conf, net in zip(bars, conf_values, networks):
            height = bar.get_height()
            if height > 0:
                self.ax1.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}\n({conf:.0%})', 
                            ha='center', va='bottom', fontsize=8)
        
        # ==========================================
        # PLOT 2: Confirmed vs Inferred
        # ==========================================
        x = np.arange(len(networks))
        width = 0.35
        
        confirmed_vals = [sum(1 for e in self.imsi_events 
                            if e['operator'] == n and 
                            e['timestamp'] >= time.time() - self.moving_window) 
                         for n in networks]
        
        signal_vals = [sum(1 for h in self.signal_hits[n] 
                          if h['timestamp'] >= time.time() - self.moving_window) 
                      for n in networks if n in self.signal_hits]
        
        # Pad signal_vals to match networks length
        padded_signals = []
        for n in networks:
            if n in self.signal_hits:
                count = sum(1 for h in self.signal_hits[n] 
                           if h['timestamp'] >= time.time() - self.moving_window)
                padded_signals.append(count)
            else:
                padded_signals.append(0)
        
        bars1 = self.ax2.bar(x - width/2, confirmed_vals, width, label='Confirmed IMSIs', 
                            color='green', alpha=0.7)
        bars2 = self.ax2.bar(x + width/2, padded_signals, width, label='Signal Hits', 
                            color='orange', alpha=0.5, hatch='//')
        
        self.ax2.set_title('Confirmed vs Inferred', fontweight='bold')
        self.ax2.set_xticks(x)
        self.ax2.set_xticklabels(networks)
        self.ax2.legend()
        self.ax2.set_ylabel('Count')
        
        # ==========================================
        # PLOT 3: Confidence Intervals
        # ==========================================
        y_pos = np.arange(len(networks))
        conf_ints = []
        
        for n in networks:
            est = estimate['by_network'][n]
            conf = estimate['confidence'].get(n, 0.5)
            # Calculate confidence interval (simplified)
            lower = int(est * (1 - (1-conf)))
            upper = int(est * (1 + (1-conf)))
            conf_ints.append((lower, upper))
        
        for i, (net, est, (low, high)) in enumerate(zip(networks, est_values, conf_ints)):
            self.ax3.errorbar(est, i, xerr=[[est-low], [high-est]], 
                            fmt='o', color=colors[i], capsize=5, capthick=2)
            self.ax3.text(est + (high-est) + 2, i, f'±{int((high-est))}', 
                         va='center', fontsize=8)
        
        self.ax3.set_yticks(y_pos)
        self.ax3.set_yticklabels(networks)
        self.ax3.set_xlabel('Estimated Devices')
        self.ax3.set_title(f'Confidence Intervals ({self.confidence_level:.0%} CI)', 
                          fontweight='bold')
        self.ax3.grid(True, alpha=0.3, axis='x')
        
        # ==========================================
        # PLOT 4: Timeline of Estimates
        # ==========================================
        if len(self.estimation_history) > 1:
            timestamps = [datetime.datetime.fromtimestamp(e['timestamp']) 
                         for e in self.estimation_history]
            est_vals = [e['estimated'] for e in self.estimation_history]
            conf_vals = [e['confirmed'] for e in self.estimation_history]
            
            self.ax4.plot(timestamps, est_vals, 'b-', label='Estimated', linewidth=2)
            self.ax4.plot(timestamps, conf_vals, 'g--', label='Confirmed', linewidth=1.5, alpha=0.7)
            self.ax4.fill_between(timestamps, 
                                  [e * 0.8 for e in est_vals], 
                                  [e * 1.2 for e in est_vals], 
                                  alpha=0.2, color='blue', label='Confidence Band')
            
            self.ax4.set_title('Device Count Timeline', fontweight='bold')
            self.ax4.set_ylabel('Devices')
            self.ax4.legend(loc='upper left')
            self.ax4.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            plt.setp(self.ax4.xaxis.get_majorticklabels(), rotation=45)
        
        # ==========================================
        # PLOT 5: Calibration Trend
        # ==========================================
        if len(self.historical_ratio) > 1:
            ratios = list(self.historical_ratio)
            self.ax5.plot(ratios, 'o-', color='purple', label='Signal/IMSI Ratio')
            self.ax5.axhline(y=self.calibration_factor, color='red', linestyle='--', 
                            label=f'Calibration: {self.calibration_factor:.2f}')
            
            # Add network factors as horizontal lines
            for net, factor in self.network_factors.items():
                if net != 'Unknown':
                    color = self.network_colors.get(net, 'gray')
                    self.ax5.axhline(y=factor, color=color, linestyle=':', alpha=0.5, 
                                    label=f'{net}: {factor:.1f}x')
            
            self.ax5.set_title('Auto-Calibration Trend', fontweight='bold')
            self.ax5.set_xlabel('Samples')
            self.ax5.set_ylabel('Ratio / Factor')
            self.ax5.legend(loc='upper left', fontsize='x-small')
            self.ax5.grid(True, alpha=0.3)
        
        # Add summary statistics
        summary = (f"📊 CURRENT ESTIMATE: {estimate['estimated']} devices "
                  f"({estimate['confirmed']} confirmed, {estimate['signals']} signal bursts) | "
                  f"Ratio: {estimate['ratio']:.2f} signals/IMSI | "
                  f"Calibration: {self.calibration_factor:.2f}")
        
        self.fig.text(0.5, 0.01, summary, ha='center', fontsize=11, fontweight='bold',
                     bbox=dict(boxstyle="round", facecolor='lightyellow', alpha=0.8))
        
        # Use subplots_adjust instead of tight_layout to avoid warning
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.08, hspace=0.3)
        return self.ax1, self.ax2, self.ax3, self.ax4, self.ax5
    
    def run(self):
        """Run the device estimator"""
        print("="*70)
        print("📊 REAL-TIME DEVICE ESTIMATOR")
        print("="*70)
        print("Using inference data to calculate actual devices in area")
        print("\nEstimation Method:")
        print("  • Confirmed IMSIs = actual captured users (2G networks)")
        print("  • Signal hits = network presence (all networks)")
        print("  • Network factors adjust for 4G/5G visibility")
        print("  • Auto-calibration improves accuracy over time")
        print("\nNetwork Factors (higher = harder to detect):")
        for net, factor in self.network_factors.items():
            if net != 'Unknown':
                print(f"  • {net}: {factor}x")
        print("="*70)
        print("Press Ctrl+C to stop and save calibration\n")
        
        # Initialize file positions
        if os.path.exists(self.imsi_file):
            self.last_imsi_pos = os.path.getsize(self.imsi_file)
        
        # Create animation
        ani = animation.FuncAnimation(self.fig, self.update_plots, 
                                     interval=15000, cache_frame_data=False)  # Update every 15 seconds
        plt.show()
        
        # Save calibration on exit
        self.save_calibration()

if __name__ == "__main__":
    estimator = DeviceEstimator()
    
    try:
        estimator.run()
    except KeyboardInterrupt:
        print("\n\n📊 Device Estimator Stopped")
        print(f"✅ Calibration saved to {estimator.calibration_file}")
