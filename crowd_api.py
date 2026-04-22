#!/usr/bin/env python3
"""
CrowdSense API Server
REST API for chatbot to access crowd data in real-time
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List
import uvicorn
import socket

app = FastAPI(
    title="CrowdSense API",
    description="Real-time crowd data from IMSI catcher",
    version="2.0.0"
)

# Enable CORS for chatbot access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your friend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DB_PATH = "crowd_sense_data.db"

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
async def root():
    """API root - shows available endpoints"""
    return {
        "name": "CrowdSense API",
        "version": "2.0.0",
        "endpoints": {
            "GET /stats": "Overall statistics",
            "GET /devices": "List all unique devices",
            "GET /devices/{imsi}": "Get specific device",
            "GET /realtime": "Real-time crowd data",
            "GET /history": "Historical crowd analysis",
            "GET /operators": "Operator distribution",
            "GET /top-devices": "Most frequent devices",
            "GET /health": "API health check"
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

@app.get("/stats")
async def get_stats():
    """Get overall statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total unique devices
    cursor.execute("SELECT COUNT(*) as count FROM imsi_records")
    total_devices = cursor.fetchone()['count']
    
    # Total detections
    cursor.execute("SELECT COUNT(*) as count FROM detection_events")
    total_detections = cursor.fetchone()['count']
    
    # Devices seen in last hour
    hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    cursor.execute("""
        SELECT COUNT(DISTINCT imsi) as count 
        FROM detection_events 
        WHERE timestamp > ?
    """, (hour_ago,))
    active_last_hour = cursor.fetchone()['count']
    
    # Latest analysis
    cursor.execute("""
        SELECT * FROM crowd_analysis 
        ORDER BY timestamp DESC LIMIT 1
    """)
    latest = cursor.fetchone()
    
    conn.close()
    
    return {
        "total_unique_devices": total_devices,
        "total_detections": total_detections,
        "active_last_hour": active_last_hour,
        "latest_analysis": dict(latest) if latest else None,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/realtime")
async def realtime_data(minutes: int = Query(5, description="Minutes of data to return")):
    """Get real-time crowd data for chatbot"""
    conn = get_db()
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    
    # Recent detections
    cursor.execute("""
        SELECT timestamp, imsi, mcc, mnc, signal_strength 
        FROM detection_events 
        WHERE timestamp > ? 
        ORDER BY timestamp DESC 
        LIMIT 50
    """, (since,))
    recent = [dict(row) for row in cursor.fetchall()]
    
    # Current active devices count
    cursor.execute("""
        SELECT COUNT(DISTINCT imsi) as count 
        FROM detection_events 
        WHERE timestamp > ?
    """, (since,))
    active = cursor.fetchone()['count']
    
    # Operator distribution in this period
    cursor.execute("""
        SELECT i.operator, COUNT(*) as count 
        FROM detection_events d
        JOIN imsi_records i ON d.imsi = i.imsi
        WHERE d.timestamp > ?
        GROUP BY i.operator
        ORDER BY count DESC
    """, (since,))
    operators = [{"operator": row['operator'], "count": row['count']} 
                 for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "period_minutes": minutes,
        "active_devices": active,
        "recent_detections": recent[:10],  # Last 10 detections
        "operator_activity": operators,
        "total_in_period": len(recent)
    }

@app.get("/devices")
async def list_devices(
    limit: int = Query(100, description="Number of devices to return"),
    operator: Optional[str] = Query(None, description="Filter by operator")
):
    """List all unique devices"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM imsi_records"
    params = []
    
    if operator:
        query += " WHERE operator = ?"
        params.append(operator)
    
    query += " ORDER BY last_seen DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "count": len(devices),
        "devices": devices
    }

@app.get("/devices/{imsi}")
async def get_device(imsi: str):
    """Get specific device details"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM imsi_records WHERE imsi = ?", (imsi,))
    device = cursor.fetchone()
    
    if not device:
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get detection history
    cursor.execute("""
        SELECT timestamp, signal_strength 
        FROM detection_events 
        WHERE imsi = ? 
        ORDER BY timestamp DESC 
        LIMIT 100
    """, (imsi,))
    history = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "device": dict(device),
        "detection_history": history
    }

@app.get("/history")
async def get_history(
    hours: int = Query(24, description="Hours of history to return"),
    limit: int = Query(100, description="Number of records")
):
    """Get historical crowd analysis"""
    conn = get_db()
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    cursor.execute("""
        SELECT * FROM crowd_analysis 
        WHERE timestamp > ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (since, limit))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "period_hours": hours,
        "records": len(history),
        "data": history
    }

@app.get("/operators")
async def operator_distribution():
    """Get current operator distribution"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT operator, COUNT(*) as count 
        FROM imsi_records 
        GROUP BY operator 
        ORDER BY count DESC
    """)
    
    distribution = [{"operator": row['operator'], "count": row['count']} 
                    for row in cursor.fetchall()]
    
    # Calculate percentages
    total = sum(d['count'] for d in distribution)
    for d in distribution:
        d['percentage'] = round((d['count'] / total * 100), 1) if total > 0 else 0
    
    conn.close()
    
    return {
        "total_devices": total,
        "distribution": distribution,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/top-devices")
async def top_devices(limit: int = Query(10, description="Number of devices")):
    """Get most frequently detected devices"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT imsi, operator, detection_count, last_seen 
        FROM imsi_records 
        ORDER BY detection_count DESC 
        LIMIT ?
    """, (limit,))
    
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "limit": limit,
        "devices": devices
    }

@app.get("/chatbot-feed")
async def chatbot_feed():
    """Optimized endpoint for chatbot - returns simple format"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get current stats
    cursor.execute("SELECT COUNT(*) FROM imsi_records")
    total = cursor.fetchone()[0]
    
    # Get active in last 5 minutes
    five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
    cursor.execute("""
        SELECT COUNT(DISTINCT imsi) FROM detection_events 
        WHERE timestamp > ?
    """, (five_min_ago,))
    active = cursor.fetchone()[0]
    
    # Get operator breakdown
    cursor.execute("""
        SELECT operator, COUNT(*) as count 
        FROM imsi_records 
        GROUP BY operator 
        ORDER BY count DESC
    """)
    operators = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
    
    # Get last 5 detections (simple format)
    cursor.execute("""
        SELECT timestamp, imsi FROM detection_events 
        ORDER BY timestamp DESC LIMIT 5
    """)
    recent = [f"{row[0]}|{row[1][-8:]}" for row in cursor.fetchall()]
    
    conn.close()
    
    # Simple string format for easy chatbot parsing
    return {
        "simple": f"TOTAL:{total}|ACTIVE:{active}|OPS:{','.join(operators)}|RECENT:{','.join(recent)}",
        "structured": {
            "total_devices": total,
            "active_5min": active,
            "operators": [dict(zip(['name','count'], op.split(':'))) for op in operators],
            "recent": [dict(zip(['time','imsi'], rec.split('|'))) for rec in recent]
        }
    }

if __name__ == "__main__":
    # Get local IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("="*60)
    print("🚀 CrowdSense API Server")
    print("="*60)
    print(f"\n📡 Server running at:")
    print(f"   Local:   http://localhost:8000")
    print(f"   Network: http://{local_ip}:8000")
    print(f"\n📚 API Documentation:")
    print(f"   Swagger UI: http://localhost:8000/docs")
    print(f"   ReDoc:      http://localhost:8000/redoc")
    print(f"\n🔗 Share with friend:")
    print(f"   http://{local_ip}:8000")
    print(f"   http://{local_ip}:8000/chatbot-feed (simplified for chatbot)")
    print(f"\n🛑 Press Ctrl+C to stop")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
