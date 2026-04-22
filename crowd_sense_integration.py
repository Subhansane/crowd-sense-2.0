#!/usr/bin/env python3
"""
CrowdSense v2.0 - IMSI Catcher Integration
Real-time crowd analysis for your IMSI data
"""

import asyncio
import os
import re
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Optional, Dict, List, Tuple
import signal
import sys

# Add path for CrowdSense modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import CrowdSense components
try:
    from crowd_sense_v2.engine.crowd_sense_engine import CrowdSenseEngine
    from crowd_sense_v2.storage.sqlite_store import SQLiteStore
    from crowd_sense_v2.analytics.crowd_analyzer import AdvancedCrowdAnalyzer
    from crowd_sense_v2.models.data_models import (
        IMSIMetadata, CellTowerInfo, DetectionEvent, CellularTechType
    )
    print("✅ CrowdSense modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you've created the crowd_sense_v2 directory structure")
    sys.exit(1)

class IMSICrowdSenseIntegrator:
    """
    Integrates CrowdSense v2.0 with your IMSI catcher
    """
    
    def __init__(self, 
                 db_path: str = "crowd_sense_data.db",
                 imsi_file: str = "imsi_output.txt",
                 analysis_interval: int = 60):
        
        self.imsi_file = imsi_file
        self.analysis_interval = analysis_interval
        self.last_position = 0
        self.running = True
        self.stats = {
            'total_processed': 0,
            'unique_ims': 0,
            'start_time': datetime.now(),
            'last_analysis': None
        }
        
        # Setup logging
        self._setup_logging()
        
        # Initialize CrowdSense components
        self.logger.info("📊 Initializing CrowdSense components...")
        self.store = SQLiteStore(db_path)
        self.analyzer = AdvancedCrowdAnalyzer(window_size=60, anomaly_threshold=2.5)
        self.engine = CrowdSenseEngine(self.store, self.analyzer)
        
        # Cache for tracking
        self.processed_ims = set()
        self.recent_detections = []
        
        # Pakistan specific mappings
        self.operator_map = {
            '06': ('Telenor', 'Telenor Pakistan'),
            '04': ('Zong', 'China Mobile'),
            '03': ('Ufone', 'Pakistan Telecommunication'),
            '01': ('Jazz', 'Jazz'),
            '07': ('Jazz', 'Jazz'),
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("IMSI-CrowdSense")
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console.setFormatter(console_format)
        self.logger.addHandler(console)
        
        # File handler
        file_handler = logging.FileHandler("crowd_sense.log")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info("\n🛑 Shutdown signal received...")
        self.running = False
    
    def parse_imsi_line(self, line: str) -> Optional[Dict]:
        """Parse IMSI line from your catcher output"""
        if not line or line.startswith('Nb IMSI') or line.startswith('stamp'):
            return None
        
        # Extract IMSI (410 06 XXXXXXX format)
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if not imsi_match:
            return None
        
        imsi_parts = imsi_match.group(0).split()
        if len(imsi_parts) < 3:
            return None
            
        mcc = imsi_parts[0]
        mnc = imsi_parts[1]
        imsi_number = imsi_parts[2]
        full_imsi = f"{mcc}{mnc}{imsi_number}"
        
        # Get operator info
        operator_info = self.operator_map.get(mnc, ('Unknown', 'Unknown'))
        operator, brand = operator_info
        
        # Extract timestamp
        timestamp = datetime.now()
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
        if time_match:
            try:
                timestamp = datetime.fromisoformat(time_match.group(1).replace(' ', 'T'))
            except:
                pass
        
        # Estimate signal strength (you may need to adjust this)
        signal = -65 - (hash(full_imsi) % 30)  # Simulated between -65 and -95
        
        # Extract cell/lac info
        lac = None
        cell_id = None
        cell_match = re.search(r'(\d+)\s*;\s*(\d+)\s*$', line)
        if cell_match:
            lac = cell_match.group(1)
            cell_id = cell_match.group(2)
        
        return {
            'imsi': full_imsi,
            'mcc': mcc,
            'mnc': mnc,
            'country': 'Pakistan',
            'operator': operator,
            'brand': brand,
            'signal_strength': signal,
            'timestamp': timestamp,
            'lac': lac,
            'cell_id': cell_id,
            'raw_line': line.strip()
        }
    
    async def process_imsi(self, data: Dict):
        """Process a single IMSI detection"""
        try:
            # Register with CrowdSense engine
            imsi_metadata = await self.engine.register_imsi(
                imsi=data['imsi'],
                mcc=data['mcc'],
                mnc=data['mnc'],
                country=data['country'],
                operator=data['operator'],
                brand=data['brand'],
                signal_strength=data['signal_strength'],
                tech_type=CellularTechType.GSM
            )
            
            # Track for stats
            if data['imsi'] not in self.processed_ims:
                self.processed_ims.add(data['imsi'])
                self.stats['unique_ims'] = len(self.processed_ims)
            
            self.stats['total_processed'] += 1
            self.recent_detections.append(data)
            
            # Keep recent detections manageable
            if len(self.recent_detections) > 1000:
                self.recent_detections = self.recent_detections[-1000:]
            
            # Log with appropriate emoji based on operator
            emoji = {
                'Telenor': '📱',
                'Zong': '🔴',
                'Ufone': '🟡',
                'Jazz': '🔵',
                'Unknown': '❓'
            }.get(data['operator'], '📡')
            
            self.logger.info(
                f"{emoji} [{self.stats['total_processed']}] {data['operator']}: {data['imsi'][-8:]}"
            )
            
            # Create detection event if we have cell info
            if data.get('lac') and data.get('cell_id'):
                tower_id = f"{data['mcc']}_{data['mnc']}_{data['lac']}_{data['cell_id']}"
                await self.engine.create_detection_event(
                    imsi=data['imsi'],
                    mcc=data['mcc'],
                    mnc=data['mnc'],
                    tower_id=tower_id,
                    signal_strength=data['signal_strength']
                )
            
        except Exception as e:
            self.logger.error(f"Error processing IMSI: {e}")
    
    async def monitor_file(self):
        """Monitor imsi_output.txt for new data"""
        if not os.path.exists(self.imsi_file):
            Path(self.imsi_file).touch()
            self.logger.info(f"Created {self.imsi_file}")
        
        self.logger.info(f"👀 Monitoring {self.imsi_file} for IMSI data...")
        
        with open(self.imsi_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            self.last_position = f.tell()
            
            while self.running:
                try:
                    line = f.readline()
                    if line:
                        data = self.parse_imsi_line(line)
                        if data:
                            await self.process_imsi(data)
                    else:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    self.logger.error(f"Error reading file: {e}")
                    await asyncio.sleep(1)
    
    async def analysis_loop(self):
        """Periodic analysis of crowd data"""
        while self.running:
            try:
                await asyncio.sleep(self.analysis_interval)
                
                if len(self.processed_ims) > 0:
                    # Generate crowd report
                    report = await self.engine.generate_crowd_report(detailed=True)
                    
                    self.stats['last_analysis'] = datetime.now()
                    
                    # Log summary
                    self.logger.info("\n" + "="*60)
                    self.logger.info("📊 CROWD ANALYSIS REPORT")
                    self.logger.info("="*60)
                    self.logger.info(f"Total Unique Devices: {report['total_unique_devices']}")
                    self.logger.info(f"Crowd Density: {report['crowd_density']:.1%}")
                    self.logger.info(f"Trend: {report['trend'].upper()}")
                    self.logger.info(f"Peak Hour: {'Yes' if report['peak_hour'] else 'No'}")
                    
                    # Operator breakdown
                    self.logger.info("\n📱 Operator Distribution:")
                    for operator, count in report['unique_operators'].items():
                        percentage = (count / report['total_unique_devices']) * 100
                        self.logger.info(f"   {operator}: {count} devices ({percentage:.1f}%)")
                    
                    # Anomalies
                    if report.get('anomalies_detected'):
                        self.logger.warning(f"\n⚠️ Anomalies Detected: {report['anomaly_count']}")
                    
                    self.logger.info("="*60 + "\n")
                    
                    # Export data periodically
                    if self.stats['total_processed'] % 1000 < self.analysis_interval:
                        await self.export_data()
                        
            except Exception as e:
                self.logger.error(f"Analysis error: {e}")
    
    async def export_data(self):
        """Export data to JSON"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crowd_export_{timestamp}.json"
            
            # Get engine stats
            engine_stats = await self.engine.get_engine_stats()
            
            # Get top devices
            top_devices = await self.engine.get_top_devices(limit=20)
            
            export = {
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats,
                'engine_stats': engine_stats,
                'top_devices': top_devices,
                'unique_operators': await self.engine.get_operator_distribution()
            }
            
            with open(filename, 'w') as f:
                json.dump(export, f, indent=2, default=str)
            
            self.logger.info(f"💾 Data exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Export error: {e}")
    
    async def status_loop(self):
        """Periodic status updates"""
        while self.running:
            await asyncio.sleep(30)
            
            uptime = datetime.now() - self.stats['start_time']
            rate = self.stats['total_processed'] / max(uptime.total_seconds(), 1)
            
            self.logger.info(
                f"📈 Status: {self.stats['unique_ims']} unique IMSIs | "
                f"{self.stats['total_processed']} total | "
                f"{rate:.1f} detections/sec"
            )
    
    async def run(self):
        """Main run loop"""
        self.logger.info("="*60)
        self.logger.info("🚀 CrowdSense v2.0 - IMSI Catcher Integration")
        self.logger.info("="*60)
        self.logger.info(f"📁 Monitoring: {self.imsi_file}")
        self.logger.info(f"⏱️  Analysis interval: {self.analysis_interval}s")
        self.logger.info(f"💾 Database: {self.store.db_path}")
        self.logger.info("="*60 + "\n")
        
        # Start the engine
        await self.engine.start()
        self.logger.info("✅ CrowdSense engine started")
        
        # Run all tasks concurrently
        tasks = [
            asyncio.create_task(self.monitor_file()),
            asyncio.create_task(self.analysis_loop()),
            asyncio.create_task(self.status_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown"""
        self.logger.info("\n🛑 Shutting down...")
        await self.engine.stop()
        await self.export_data()
        self.logger.info("✅ Shutdown complete")

async def main():
    """Main entry point"""
    # Create integrator
    integrator = IMSICrowdSenseIntegrator(
        db_path="crowd_sense_data.db",
        imsi_file="imsi_output.txt",
        analysis_interval=60  # Analyze every minute
    )
    
    try:
        await integrator.run()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
