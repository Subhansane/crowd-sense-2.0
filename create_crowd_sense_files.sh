#!/bin/bash
# Create all CrowdSense v2.0 files

cd ~/IMSI-catcher-master

# Create directory structure
mkdir -p crowd_sense_v2/{models,interfaces,analytics,engine,storage}

# ==========================================
# Create __init__.py files
# ==========================================
echo '"""CrowdSense v2.0 - Advanced Crowd Sensing Platform"""' > crowd_sense_v2/__init__.py

cat > crowd_sense_v2/models/__init__.py << 'EOF'
"""Data models for CrowdSense"""
from .data_models import IMSIMetadata, CellTowerInfo, CrowdAnalysis, DetectionEvent, CellularTechType

__all__ = ['IMSIMetadata', 'CellTowerInfo', 'CrowdAnalysis', 'DetectionEvent', 'CellularTechType']
EOF

cat > crowd_sense_v2/interfaces/__init__.py << 'EOF'
"""Interfaces for CrowdSense"""
from .base_interfaces import DataStore, SignalProcessor, DataAnalyzer, EventHandler, DataSource

__all__ = ['DataStore', 'SignalProcessor', 'DataAnalyzer', 'EventHandler', 'DataSource']
EOF

cat > crowd_sense_v2/analytics/__init__.py << 'EOF'
"""Analytics modules for CrowdSense"""
from .crowd_analyzer import AdvancedCrowdAnalyzer

__all__ = ['AdvancedCrowdAnalyzer']
EOF

cat > crowd_sense_v2/engine/__init__.py << 'EOF'
"""Engine module for CrowdSense"""
from .crowd_sense_engine import CrowdSenseEngine

__all__ = ['CrowdSenseEngine']
EOF

cat > crowd_sense_v2/storage/__init__.py << 'EOF'
"""Storage modules for CrowdSense"""
from .sqlite_store import SQLiteStore

__all__ = ['SQLiteStore']
EOF

# ==========================================
# Create data_models.py
# ==========================================
cat > crowd_sense_v2/models/data_models.py << 'EOF'
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from collections import deque

class CellularTechType(Enum):
    """Supported cellular technologies"""
    GSM = "gsm"
    LTE = "lte"
    NR = "nr"  # 5G
    UMTS = "umts"
    CDMA = "cdma"

@dataclass
class IMSIMetadata:
    """IMSI observation data model"""
    imsi: str
    mcc: str
    mnc: str
    country: str
    operator: str
    brand: str
    first_seen: datetime
    last_seen: datetime
    detection_count: int = 1
    arfcn_list: List[int] = field(default_factory=list)
    signal_strength: float = 0.0
    tech_type: CellularTechType = CellularTechType.GSM
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def to_dict(self):
        """Convert to dictionary"""
        data = asdict(self)
        data['tech_type'] = self.tech_type.value
        data['first_seen'] = self.first_seen.isoformat()
        data['last_seen'] = self.last_seen.isoformat()
        return data
    
    def update_sighting(self, signal_strength: float = 0.0):
        """Update last seen time and increment counter"""
        self.last_seen = datetime.now()
        self.detection_count += 1
        self.signal_strength = signal_strength

@dataclass
class CellTowerInfo:
    """Cell tower information"""
    mcc: str
    mnc: str
    lac: str
    cell_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    first_detected: Optional[datetime] = None
    last_detected: Optional[datetime] = None
    tech_type: CellularTechType = CellularTechType.GSM
    signal_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    imsi_count: int = 0
    
    def add_signal_sample(self, signal_dbm: float, snr_db: float = 0.0):
        """Add signal strength sample"""
        self.signal_samples.append({
            'timestamp': datetime.now(),
            'signal_dbm': signal_dbm,
            'snr_db': snr_db
        })
    
    def get_tower_id(self) -> str:
        """Generate unique tower ID"""
        return f"{self.mcc}_{self.mnc}_{self.lac}_{self.cell_id}"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'tower_id': self.get_tower_id(),
            'mcc': self.mcc,
            'mnc': self.mnc,
            'lac': self.lac,
            'cell_id': self.cell_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'tech_type': self.tech_type.value,
            'imsi_count': self.imsi_count
        }

@dataclass
class CrowdAnalysis:
    """Crowd analysis results"""
    timestamp: datetime
    tower_id: str
    total_devices: int
    unique_operators: Dict[str, int]
    signal_distribution: Dict[str, float]
    crowd_density: float  # 0-1 normalized
    trend: str  # "increasing", "stable", "decreasing"
    peak_hour: bool = False
    anomaly_detected: bool = False
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'tower_id': self.tower_id,
            'total_devices': self.total_devices,
            'unique_operators': self.unique_operators,
            'crowd_density': self.crowd_density,
            'trend': self.trend,
            'peak_hour': self.peak_hour,
            'anomaly_detected': self.anomaly_detected
        }

@dataclass
class DetectionEvent:
    """IMSI detection event"""
    event_id: str
    timestamp: datetime
    imsi: str
    mcc: str
    mnc: str
    tower_id: str
    signal_strength: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'imsi': self.imsi,
            'mcc': self.mcc,
            'mnc': self.mnc,
            'tower_id': self.tower_id,
            'signal_strength': self.signal_strength
        }
EOF

# ==========================================
# Create base_interfaces.py
# ==========================================
cat > crowd_sense_v2/interfaces/base_interfaces.py << 'EOF'
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from crowd_sense_v2.models.data_models import IMSIMetadata, CellTowerInfo, CrowdAnalysis, DetectionEvent

class DataStore(ABC):
    """Abstract base class for data persistence"""
    
    @abstractmethod
    async def save_imsi(self, imsi_data: IMSIMetadata) -> bool:
        """Save IMSI metadata to storage"""
        pass
    
    @abstractmethod
    async def get_imsi(self, imsi: str) -> Optional[IMSIMetadata]:
        """Retrieve IMSI metadata"""
        pass
    
    @abstractmethod
    async def get_all_imsi(self, limit: int = 1000) -> List[IMSIMetadata]:
        """Get all IMSI records"""
        pass
    
    @abstractmethod
    async def save_cell_info(self, cell: CellTowerInfo) -> bool:
        """Save cell tower information"""
        pass
    
    @abstractmethod
    async def get_cell_info(self, tower_id: str) -> Optional[CellTowerInfo]:
        """Retrieve cell tower information"""
        pass
    
    @abstractmethod
    async def save_crowd_analysis(self, analysis: CrowdAnalysis) -> bool:
        """Save crowd analysis results"""
        pass
    
    @abstractmethod
    async def get_crowd_analysis(self, tower_id: str, limit: int = 100) -> List[CrowdAnalysis]:
        """Get historical crowd analysis for a tower"""
        pass
    
    @abstractmethod
    async def save_detection_event(self, event: DetectionEvent) -> bool:
        """Save detection event"""
        pass
    
    @abstractmethod
    async def delete_old_records(self, days: int = 30) -> int:
        """Delete records older than specified days"""
        pass

class SignalProcessor(ABC):
    """Abstract base for signal processing strategies"""
    
    @abstractmethod
    def process(self, raw_signal: bytes) -> Dict:
        """Process raw signal data"""
        pass
    
    @abstractmethod
    def decode_imsi(self, data: bytes) -> Optional[str]:
        """Extract IMSI from signal"""
        pass
    
    @abstractmethod
    def extract_cell_info(self, data: bytes) -> Optional[Dict]:
        """Extract cell information from signal"""
        pass

class DataAnalyzer(ABC):
    """Abstract base for data analysis"""
    
    @abstractmethod
    def analyze_crowd(self, imsi_list: List[IMSIMetadata], tower_id: str = "unknown") -> Optional[CrowdAnalysis]:
        """Analyze crowd characteristics"""
        pass
    
    @abstractmethod
    def detect_anomalies(self, imsi_list: List[IMSIMetadata]) -> List[Dict]:
        """Detect anomalous patterns"""
        pass
    
    @abstractmethod
    def predict_trend(self, history: List[CrowdAnalysis]) -> str:
        """Predict crowd trend"""
        pass
    
    @abstractmethod
    def calculate_density(self, device_count: int, area_sqkm: float = 1.0) -> float:
        """Calculate crowd density"""
        pass

class EventHandler(ABC):
    """Abstract base for event handling"""
    
    @abstractmethod
    async def on_imsi_detected(self, imsi: IMSIMetadata) -> None:
        """Handle IMSI detection"""
        pass
    
    @abstractmethod
    async def on_cell_detected(self, cell: CellTowerInfo) -> None:
        """Handle cell tower detection"""
        pass
    
    @abstractmethod
    async def on_crowd_analysis_complete(self, analysis: CrowdAnalysis) -> None:
        """Handle completed crowd analysis"""
        pass
    
    @abstractmethod
    async def on_anomaly_detected(self, anomaly_data: Dict) -> None:
        """Handle anomaly detection"""
        pass

class DataSource(ABC):
    """Abstract base for data sources"""
    
    @abstractmethod
    async def start(self) -> None:
        """Start receiving data"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop receiving data"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check connection status"""
        pass
EOF

# ==========================================
# Create crowd_analyzer.py
# ==========================================
cat > crowd_sense_v2/analytics/crowd_analyzer.py << 'EOF'
import logging
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict, deque
import numpy as np
from crowd_sense_v2.interfaces.base_interfaces import DataAnalyzer
from crowd_sense_v2.models.data_models import IMSIMetadata, CrowdAnalysis

class AdvancedCrowdAnalyzer(DataAnalyzer):
    """Statistical and ML-based crowd analyzer"""
    
    def __init__(self, window_size: int = 60, anomaly_threshold: float = 2.5):
        self.window_size = window_size
        self.anomaly_threshold = anomaly_threshold
        self.history = deque(maxlen=window_size)
        self.logger = logging.getLogger(__name__)
    
    def analyze_crowd(self, imsi_list: List[IMSIMetadata], 
                     tower_id: str = "unknown") -> Optional[CrowdAnalysis]:
        """Analyze crowd characteristics"""
        if not imsi_list:
            return None
        
        # Count operators and collect metrics
        operator_counts = defaultdict(int)
        signal_strengths = []
        detection_counts = []
        
        for imsi in imsi_list:
            operator_counts[imsi.operator] += 1
            signal_strengths.append(imsi.signal_strength)
            detection_counts.append(imsi.detection_count)
        
        # Calculate metrics
        total_devices = len(imsi_list)
        avg_signal = np.mean(signal_strengths) if signal_strengths else 0.0
        std_signal = np.std(signal_strengths) if len(signal_strengths) > 1 else 0.0
        
        # Add to history for trend analysis
        self.history.append(total_devices)
        trend = self._calculate_trend()
        
        # Calculate crowd density (devices per 1000)
        crowd_density = min(total_devices / 1000.0, 1.0)
        
        # Detect peak hours
        peak_hour = self._is_peak_hour()
        
        # Detect anomalies
        anomaly_detected = self._detect_anomalies(total_devices, avg_signal)
        
        return CrowdAnalysis(
            timestamp=datetime.now(),
            tower_id=tower_id,
            total_devices=total_devices,
            unique_operators=dict(operator_counts),
            signal_distribution={
                "avg": float(avg_signal),
                "std": float(std_signal),
                "min": float(np.min(signal_strengths)) if signal_strengths else 0.0,
                "max": float(np.max(signal_strengths)) if signal_strengths else 0.0,
                "device_count": total_devices
            },
            crowd_density=crowd_density,
            trend=trend,
            peak_hour=peak_hour,
            anomaly_detected=anomaly_detected
        )
    
    def detect_anomalies(self, imsi_list: List[IMSIMetadata]) -> List[Dict]:
        """Detect anomalous patterns"""
        anomalies = []
        
        # Check for sudden device count spike
        if len(self.history) > 1:
            recent_avg = np.mean(list(self.history)[-5:]) if len(self.history) >= 5 else self.history[-1]
            current = len(imsi_list)
            
            if current > recent_avg * 2:  # More than 2x average
                anomalies.append({
                    'type': 'device_spike',
                    'severity': 'high',
                    'description': f'Device count increased from {recent_avg:.0f} to {current}',
                    'timestamp': datetime.now()
                })
        
        # Check for unusual operator distribution
        if len(imsi_list) > 10:
            operator_counts = defaultdict(int)
            for imsi in imsi_list:
                operator_counts[imsi.operator] += 1
            
            for operator, count in operator_counts.items():
                percentage = (count / len(imsi_list)) * 100
                if percentage > 80:  # More than 80% from one operator
                    anomalies.append({
                        'type': 'operator_skew',
                        'severity': 'medium',
                        'description': f'Operator {operator} has {percentage:.1f}% of devices',
                        'timestamp': datetime.now()
                    })
        
        # Check for signal strength anomalies
        signal_strengths = [imsi.signal_strength for imsi in imsi_list if imsi.signal_strength != 0]
        if len(signal_strengths) > 5:
            mean_signal = np.mean(signal_strengths)
            std_signal = np.std(signal_strengths)
            
            for imsi in imsi_list:
                if imsi.signal_strength != 0:
                    z_score = abs((imsi.signal_strength - mean_signal) / std_signal) if std_signal > 0 else 0
                    if z_score > self.anomaly_threshold:
                        anomalies.append({
                            'type': 'signal_anomaly',
                            'severity': 'low',
                            'description': f'IMSI {imsi.imsi} has unusual signal strength: {imsi.signal_strength}dBm',
                            'timestamp': datetime.now(),
                            'imsi': imsi.imsi
                        })
        
        return anomalies
    
    def predict_trend(self, history: List[CrowdAnalysis]) -> str:
        """Predict crowd trend based on history"""
        if not history or len(history) < 2:
            return "stable"
        
        # Sort by timestamp
        sorted_history = sorted(history, key=lambda x: x.timestamp)
        device_counts = [h.total_devices for h in sorted_history[-20:]]
        
        if len(device_counts) >= 2:
            recent_avg = np.mean(device_counts[-5:]) if len(device_counts) >= 5 else np.mean(device_counts)
            older_avg = np.mean(device_counts[:-5]) if len(device_counts) > 5 else device_counts[0]
            
            change_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            
            if change_pct > 20:
                return "increasing"
            elif change_pct < -20:
                return "decreasing"
        
        return "stable"
    
    def calculate_density(self, device_count: int, area_sqkm: float = 1.0) -> float:
        """Calculate crowd density (devices per square km)"""
        if area_sqkm <= 0:
            return 0.0
        
        density = device_count / area_sqkm
        # Normalize to 0-1 range (assuming max 1000 devices/sqkm is 1.0)
        normalized_density = min(density / 1000.0, 1.0)
        return normalized_density
    
    def _calculate_trend(self) -> str:
        """Calculate trend based on recent history"""
        if len(self.history) < 2:
            return "stable"
        
        recent = list(self.history)
        if len(recent) >= 10:
            recent_5 = np.mean(recent[-5:])
            older_5 = np.mean(recent[-10:-5])
            
            change_pct = ((recent_5 - older_5) / older_5 * 100) if older_5 > 0 else 0
            
            if change_pct > 15:
                return "increasing"
            elif change_pct < -15:
                return "decreasing"
        
        return "stable"
    
    def _is_peak_hour(self) -> bool:
        """Determine if current time is a peak hour"""
        current_hour = datetime.now().hour
        # Typical peak hours: 7-9 AM, 12-1 PM, 5-8 PM
        peak_hours = [7, 8, 12, 17, 18, 19, 20]
        return current_hour in peak_hours
    
    def _detect_anomalies(self, device_count: int, avg_signal: float) -> bool:
        """Quick anomaly detection"""
        if len(self.history) < 5:
            return False
        
        recent_avg = np.mean(list(self.history)[-5:])
        current_std = np.std(list(self.history)[-5:])
        
        # Check if current count is beyond 2 standard deviations
        if current_std > 0:
            z_score = abs((device_count - recent_avg) / current_std)
            return z_score > 2.0
        
        return False
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        if not self.history:
            return {}
        
        history_list = list(self.history)
        return {
            'total_observations': len(history_list),
            'mean_devices': float(np.mean(history_list)),
            'median_devices': float(np.median(history_list)),
            'std_devices': float(np.std(history_list)),
            'min_devices': int(np.min(history_list)),
            'max_devices': int(np.max(history_list))
        }
EOF

# ==========================================
# Create crowd_sense_engine.py
# ==========================================
cat > crowd_sense_v2/engine/crowd_sense_engine.py << 'EOF'
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import defaultdict
import json

from crowd_sense_v2.interfaces.base_interfaces import DataStore, DataAnalyzer, EventHandler
from crowd_sense_v2.models.data_models import IMSIMetadata, CellTowerInfo, CrowdAnalysis, DetectionEvent, CellularTechType

class CrowdSenseEngine:
    """Main orchestrator for crowd sensing operations"""
    
    def __init__(self, data_store: DataStore, analyzer: DataAnalyzer, 
                 event_handler: Optional[EventHandler] = None):
        self.data_store = data_store
        self.analyzer = analyzer
        self.event_handler = event_handler
        
        # In-memory caches
        self.imsi_cache: Dict[str, IMSIMetadata] = {}
        self.cell_towers: Dict[str, CellTowerInfo] = {}
        
        # State management
        self.running = False
        self.analysis_interval = 60  # seconds
        self.cleanup_interval = 3600  # seconds
        
        # Statistics
        self.stats = {
            'imsi_count': 0,
            'cell_count': 0,
            'events_processed': 0,
            'analysis_runs': 0,
            'start_time': None
        }
        
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("CrowdSenseEngine")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    async def start(self):
        """Start the sensing engine"""
        if self.running:
            self.logger.warning("Engine already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        self.logger.info("🚀 CrowdSense Engine started")
        
        # Start background tasks
        asyncio.create_task(self._analysis_loop())
        asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the sensing engine"""
        self.running = False
        self.logger.info("🛑 CrowdSense Engine stopped")
        
        # Persist cache to database
        await self._flush_cache()
    
    async def register_imsi(self, imsi: str, mcc: str, mnc: str,
                          country: str, operator: str, brand: str,
                          signal_strength: float = 0.0,
                          latitude: Optional[float] = None,
                          longitude: Optional[float] = None,
                          tech_type: CellularTechType = CellularTechType.GSM) -> IMSIMetadata:
        """Register or update IMSI sighting"""        
        now = datetime.now()
        
        if imsi in self.imsi_cache:
            # Update existing
            existing = self.imsi_cache[imsi]
            existing.update_sighting(signal_strength)
            existing.latitude = latitude or existing.latitude
            existing.longitude = longitude or existing.longitude
        else:
            # Create new
            existing = IMSIMetadata(
                imsi=imsi, mcc=mcc, mnc=mnc, country=country,
                operator=operator, brand=brand, first_seen=now,
                last_seen=now, signal_strength=signal_strength,
                latitude=latitude, longitude=longitude,
                tech_type=tech_type
            )
            self.imsi_cache[imsi] = existing
            self.stats['imsi_count'] = len(self.imsi_cache)
            self.logger.info(f"✅ New IMSI registered: {imsi} ({operator})")
        
        # Persist to database
        await self.data_store.save_imsi(existing)
        
        # Trigger event handler
        if self.event_handler:
            await self.event_handler.on_imsi_detected(existing)
        
        return existing
    
    async def register_cell_tower(self, mcc: str, mnc: str, lac: str,
                                 cell_id: str, latitude: Optional[float] = None,
                                 longitude: Optional[float] = None,
                                 tech_type: CellularTechType = CellularTechType.GSM) -> CellTowerInfo:
        """Register or update cell tower"""        
        tower_key = f"{mcc}_{mnc}_{lac}_{cell_id}"
        now = datetime.now()
        
        if tower_key in self.cell_towers:
            tower = self.cell_towers[tower_key]
            tower.last_detected = now
        else:
            tower = CellTowerInfo(
                mcc=mcc, mnc=mnc, lac=lac, cell_id=cell_id,
                latitude=latitude, longitude=longitude,
                first_detected=now, last_detected=now,
                tech_type=tech_type
            )
            self.cell_towers[tower_key] = tower
            self.stats['cell_count'] = len(self.cell_towers)
            self.logger.info(f"🔔 New cell tower detected: {tower_key}")
        
        # Persist to database
        await self.data_store.save_cell_info(tower)
        
        # Trigger event handler
        if self.event_handler:
            await self.event_handler.on_cell_detected(tower)
        
        return tower
    
    async def create_detection_event(self, imsi: str, mcc: str, mnc: str,
                                    tower_id: str, signal_strength: float,
                                    latitude: Optional[float] = None,
                                    longitude: Optional[float] = None) -> DetectionEvent:
        """Create and store a detection event"""        
        event = DetectionEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            imsi=imsi, mcc=mcc, mnc=mnc,
            tower_id=tower_id, signal_strength=signal_strength,
            latitude=latitude, longitude=longitude
        )
        
        await self.data_store.save_detection_event(event)
        self.stats['events_processed'] += 1
        
        return event
    
    async def generate_crowd_report(self, tower_id: Optional[str] = None,
                                   detailed: bool = False) -> Dict:
        """Generate comprehensive crowd analysis report"""        
        if not self.imsi_cache:
            return {
                "status": "no_data",
                "message": "No IMSI data available for analysis"
            }
        
        imsi_list = list(self.imsi_cache.values())
        
        # Generate analysis
        analysis = self.analyzer.analyze_crowd(imsi_list, tower_id or "global")
        
        if analysis:
            # Save to database
            await self.data_store.save_crowd_analysis(analysis)
        
        # Detect anomalies
        anomalies = self.analyzer.detect_anomalies(imsi_list)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_unique_devices": analysis.total_devices if analysis else 0,
            "unique_operators": analysis.unique_operators if analysis else {},
            "crowd_density": analysis.crowd_density if analysis else 0.0,
            "trend": analysis.trend if analysis else "unknown",
            "peak_hour": analysis.peak_hour if analysis else False,
            "anomalies_detected": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "cell_towers_active": len(self.cell_towers),
            "statistics": self.analyzer.get_statistics()
        }
        
        if detailed:
            report['signal_metrics'] = analysis.signal_distribution if analysis else {}
            report['anomalies'] = anomalies
            report['top_operators'] = dict(sorted(
                (analysis.unique_operators if analysis else {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5])
        
        return report
    
    async def get_operator_distribution(self) -> Dict[str, int]:
        """Get distribution of devices by operator"""
        distribution = defaultdict(int)
        for imsi in self.imsi_cache.values():
            distribution[imsi.operator] += 1
        return dict(distribution)
    
    async def get_top_devices(self, limit: int = 10) -> List[Dict]:
        """Get most frequently detected devices"""
        sorted_imsi = sorted(
            self.imsi_cache.values(),
            key=lambda x: x.detection_count,
            reverse=True
        )
        return [imsi.to_dict() for imsi in sorted_imsi[:limit]]
    
    async def get_engine_stats(self) -> Dict:
        """Get engine statistics"""
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
        else:
            uptime = None
        
        return {
            **self.stats,
            'uptime_seconds': uptime.total_seconds() if uptime else 0,
            'current_imsi_in_memory': len(self.imsi_cache),
            'current_cells_in_memory': len(self.cell_towers)
        }
    
    async def _analysis_loop(self):
        """Periodic analysis loop"""
        while self.running:
            try:
                await asyncio.sleep(self.analysis_interval)
                
                if self.imsi_cache:
                    report = await self.generate_crowd_report()
                    self.stats['analysis_runs'] += 1
                    self.logger.info(f"📊 Analysis run #{self.stats['analysis_runs']}: {report['total_unique_devices']} devices")
                    
                    # Trigger event handler
                    if self.event_handler and report.get('anomalies_detected'):
                        await self.event_handler.on_anomaly_detected(report)
            
            except Exception as e:
                self.logger.error(f"Error in analysis loop: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup loop"""
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Delete old records (older than 30 days)
                deleted = await self.data_store.delete_old_records(days=30)
                if deleted > 0:
                    self.logger.info(f"🧹 Cleanup: Deleted {deleted} old records")
            
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _flush_cache(self):
        """Flush in-memory cache to database"""
        for imsi in self.imsi_cache.values():
            await self.data_store.save_imsi(imsi)
        
        for tower in self.cell_towers.values():
            await self.data_store.save_cell_info(tower)
        
        self.logger.info("💾 Cache flushed to database")
    
    async def export_to_json(self, filepath: str) -> bool:
        """Export current state to JSON"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'engine_stats': await self.get_engine_stats(),
                'imsi_devices': [imsi.to_dict() for imsi in self.imsi_cache.values()],
                'cell_towers': [tower.to_dict() for tower in self.cell_towers.values()],
                'operator_distribution': await self.get_operator_distribution(),
                'top_devices': await self.get_top_devices()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"✅ Data exported to {filepath}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return False
EOF

# ==========================================
# Create sqlite_store.py
# ==========================================
cat > crowd_sense_v2/storage/sqlite_store.py << 'EOF'
"""
SQLite storage implementation for CrowdSense v2.0
"""

import aiosqlite
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from crowd_sense_v2.models.data_models import IMSIMetadata, CellTowerInfo, CrowdAnalysis, DetectionEvent

class SQLiteStore:
    """SQLite-based data storage"""
    
    def __init__(self, db_path: str = "crowd_sense.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        import asyncio
        asyncio.create_task(self._create_tables())
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            # IMSI table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS imsi_records (
                    imsi TEXT PRIMARY KEY,
                    mcc TEXT,
                    mnc TEXT,
                    country TEXT,
                    operator TEXT,
                    brand TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    detection_count INTEGER,
                    tech_type TEXT,
                    signal_strength REAL,
                    latitude REAL,
                    longitude REAL,
                    metadata TEXT
                )
            ''')
            
            # Cell towers table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cell_towers (
                    tower_id TEXT PRIMARY KEY,
                    mcc TEXT,
                    mnc TEXT,
                    lac TEXT,
                    cell_id TEXT,
                    latitude REAL,
                    longitude REAL,
                    first_detected TIMESTAMP,
                    last_detected TIMESTAMP,
                    tech_type TEXT,
                    imsi_count INTEGER,
                    signal_samples TEXT
                )
            ''')
            
            # Detection events table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS detection_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP,
                    imsi TEXT,
                    mcc TEXT,
                    mnc TEXT,
                    tower_id TEXT,
                    signal_strength REAL,
                    latitude REAL,
                    longitude REAL
                )
            ''')
            
            # Crowd analysis table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS crowd_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    tower_id TEXT,
                    total_devices INTEGER,
                    operator_distribution TEXT,
                    crowd_density REAL,
                    trend TEXT,
                    peak_hour BOOLEAN,
                    anomaly_detected BOOLEAN,
                    metadata TEXT
                )
            ''')
            
            await db.commit()
    
    async def save_imsi(self, imsi_data: IMSIMetadata) -> bool:
        """Save IMSI metadata"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO imsi_records 
                (imsi, mcc, mnc, country, operator, brand, first_seen, last_seen, 
                 detection_count, tech_type, signal_strength, latitude, longitude, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                imsi_data.imsi, imsi_data.mcc, imsi_data.mnc, imsi_data.country,
                imsi_data.operator, imsi_data.brand, imsi_data.first_seen.isoformat(),
                imsi_data.last_seen.isoformat(), imsi_data.detection_count,
                imsi_data.tech_type.value, imsi_data.signal_strength,
                imsi_data.latitude, imsi_data.longitude, json.dumps(imsi_data.arfcn_list)
            ))
            await db.commit()
            return True
    
    async def save_detection_event(self, event: DetectionEvent) -> bool:
        """Save detection event"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO detection_events 
                (event_id, timestamp, imsi, mcc, mnc, tower_id, signal_strength, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.timestamp.isoformat(), event.imsi,
                event.mcc, event.mnc, event.tower_id, event.signal_strength,
                event.latitude, event.longitude
            ))
            await db.commit()
            return True
    
    async def save_crowd_analysis(self, analysis: CrowdAnalysis) -> bool:
        """Save crowd analysis"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO crowd_analysis 
                (timestamp, tower_id, total_devices, operator_distribution, 
                 crowd_density, trend, peak_hour, anomaly_detected, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.timestamp.isoformat(), analysis.tower_id, analysis.total_devices,
                json.dumps(analysis.unique_operators), analysis.crowd_density,
                analysis.trend, analysis.peak_hour, analysis.anomaly_detected,
                json.dumps(analysis.signal_distribution)
            ))
            await db.commit()
            return True
    
    async def get_all_imsi(self, limit: int = 1000) -> List[IMSIMetadata]:
        """Get all IMSI records"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM imsi_records ORDER BY last_seen DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            # Convert rows back to IMSIMetadata objects (simplified)
            return [dict(row) for row in rows]
    
    async def delete_old_records(self, days: int = 30) -> int:
        """Delete records older than specified days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM detection_events WHERE timestamp < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            await db.commit()
            return deleted
EOF

# ==========================================
# Create requirements.txt
# ==========================================
cat > requirements.txt << 'EOF'
numpy>=1.21.0
pandas>=1.3.0
aiosqlite>=0.17.0
fastapi>=0.95.0
uvicorn>=0.21.0
pydantic>=1.9.0
matplotlib>=3.5.0
plotly>=5.0.0
scikit-learn>=1.0.0
python-json-logger>=2.0.0
EOF

echo "✅ All CrowdSense v2.0 files created successfully!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source crowd_sense_env/bin/activate"
echo "2. Install requirements: pip install -r requirements.txt"
echo "3. Run integration: ./run_crowd_sense.sh"
