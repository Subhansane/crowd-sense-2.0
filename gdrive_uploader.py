#!/usr/bin/env python3
"""
Google Drive Auto-Uploader for IMSI Data
Your friend can access files instantly via Google Drive share
"""

import os
import time
import hashlib
from datetime import datetime
import subprocess

# ==========================================
# CONFIGURATION
# ==========================================
SOURCE_FILE = "imsi_output.txt"
GDRIVE_FOLDER = "google:IMSI_Data"  # 'google' is the remote name you used
CHECK_INTERVAL = 15  # seconds

class GDriveUploader:
    def __init__(self):
        self.last_hash = ""
        self.upload_count = 0
        self.last_size = 0
        
        print("="*60)
        print("☁️  GOOGLE DRIVE IMSI UPLOADER")
        print("="*60)
        print(f"📁 Watching: {SOURCE_FILE}")
        print(f"☁️  Uploading to: Google Drive/IMSI_Data")
        print("="*60)
        
        # Create folder on Google Drive
        os.system(f"rclone mkdir {GDRIVE_FOLDER}")
        print("✅ Google Drive folder ready")
    
    def get_file_hash(self):
        """Detect if file changed"""
        if not os.path.exists(SOURCE_FILE):
            return ""
        return str(os.path.getmtime(SOURCE_FILE)) + str(os.path.getsize(SOURCE_FILE))
    
    def upload_to_drive(self):
        """Upload file to Google Drive"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Upload with timestamp
        dest_name = f"imsi_{timestamp}.txt"
        cmd = f"rclone copy {SOURCE_FILE} {GDRIVE_FOLDER}/ --include imsi_output.txt"
        
        # Also copy as dated file
        temp_file = f"/tmp/{dest_name}"
        os.system(f"cp {SOURCE_FILE} {temp_file}")
        os.system(f"rclone copy {temp_file} {GDRIVE_FOLDER}/")
        os.remove(temp_file)
        
        # Update latest copy
        os.system(f"rclone copy {SOURCE_FILE} {GDRIVE_FOLDER}/latest.txt")
        
        self.upload_count += 1
        current_size = os.path.getsize(SOURCE_FILE)
        new_records = current_size - self.last_size if self.last_size > 0 else 0
        
        print(f"✅ [{self.upload_count}] Uploaded: {dest_name} (+{new_records} bytes)")
        self.last_size = current_size
    
    def run(self):
        """Main loop"""
        print("\n👀 Monitoring for changes... (Press Ctrl+C to stop)\n")
        
        while True:
            try:
                if os.path.exists(SOURCE_FILE):
                    current_hash = self.get_file_hash()
                    
                    if current_hash and current_hash != self.last_hash:
                        self.upload_to_drive()
                        self.last_hash = current_hash
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print(f"\n\n👋 Stopped. Total uploads: {self.upload_count}")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    uploader = GDriveUploader()
    uploader.run()
