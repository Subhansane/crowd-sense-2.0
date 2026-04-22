#!/usr/bin/env python3
"""
Remove duplicate IMSIs from Google Drive files
Keeps only unique IMSIs with latest timestamp
"""

import os
import re
import tempfile
from datetime import datetime
from collections import defaultdict

# ==========================================
# CONFIGURATION
#==========================================
GDRIVE_FOLDER = "google:IMSI_Data"  # Your Google Drive folder
LOCAL_TEMP = "/tmp/imsi_deduplicate"

class IMSIDeduplicator:
    def __init__(self):
        self.unique_ims = {}
        self.stats = {
            'total_lines': 0,
            'unique_ims': 0,
            'duplicates_removed': 0
        }
        
    def download_files(self):
        """Download all files from Google Drive"""
        print("📥 Downloading files from Google Drive...")
        os.makedirs(LOCAL_TEMP, exist_ok=True)
        os.system(f"rclone copy {GDRIVE_FOLDER} {LOCAL_TEMP}")
        
        files = os.listdir(LOCAL_TEMP)
        print(f"✅ Downloaded {len(files)} files")
        return files
    
    def extract_imsi(self, line):
        """Extract IMSI number from line"""
        # Look for 410 XX XXXXXX pattern
        imsi_match = re.search(r'410\s+0[3467]\s+\d+', line)
        if imsi_match:
            return imsi_match.group(0).replace(' ', '')
        return None
    
    def extract_timestamp(self, line):
        """Extract timestamp from line"""
        time_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if time_match:
            return time_match.group(0)
        return None
    
    def process_files(self, files):
        """Process all files and find unique IMSIs"""
        print("\n🔍 Processing files for duplicates...")
        
        for filename in files:
            filepath = os.path.join(LOCAL_TEMP, filename)
            try:
                with open(filepath, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        self.stats['total_lines'] += 1
                        
                        imsi = self.extract_imsi(line)
                        if imsi:
                            timestamp = self.extract_timestamp(line) or f"line_{line_num}"
                            
                            # Keep only the latest occurrence of each IMSI
                            if imsi not in self.unique_ims or timestamp > self.unique_ims[imsi]['timestamp']:
                                if imsi in self.unique_ims:
                                    self.stats['duplicates_removed'] += 1
                                self.unique_ims[imsi] = {
                                    'line': line,
                                    'timestamp': timestamp,
                                    'source': filename
                                }
            except Exception as e:
                print(f"⚠️ Error processing {filename}: {e}")
        
        self.stats['unique_ims'] = len(self.unique_ims)
    
    def create_cleaned_files(self):
        """Create new files with only unique IMSIs"""
        print("\n📝 Creating deduplicated files...")
        
        # Group by operator
        operator_files = defaultdict(list)
        
        for imsi, data in self.unique_ims.items():
            # Determine operator
            operator = "Unknown"
            if "41006" in imsi:
                operator = "Telenor"
            elif "41004" in imsi:
                operator = "Zong"
            elif "41003" in imsi:
                operator = "Ufone"
            elif "41001" in imsi or "41007" in imsi:
                operator = "Jazz"
            
            operator_files[operator].append(data['line'])
        
        # Create master file with all unique IMSIs
        master_path = os.path.join(LOCAL_TEMP, "MASTER_unique_imsi.txt")
        with open(master_path, 'w') as f:
            f.write(f"# Unique IMSIs - Generated {datetime.now()}\n")
            f.write(f"# Total: {self.stats['unique_ims']}\n")
            f.write("#" + "="*50 + "\n\n")
            
            for imsi, data in sorted(self.unique_ims.items()):
                f.write(data['line'])
        
        # Create operator-specific files
        for operator, lines in operator_files.items():
            op_path = os.path.join(LOCAL_TEMP, f"{operator}_unique.txt")
            with open(op_path, 'w') as f:
                f.write(f"# {operator} Unique IMSIs - {len(lines)} devices\n")
                f.write("#" + "="*50 + "\n")
                for line in lines:
                    f.write(line)
        
        print(f"✅ Created master file with {self.stats['unique_ims']} unique IMSIs")
        
        # Create statistics file
        stats_path = os.path.join(LOCAL_TEMP, "STATISTICS.txt")
        with open(stats_path, 'w') as f:
            f.write("="*60 + "\n")
            f.write("IMSI DEDUPLICATION STATISTICS\n")
            f.write("="*60 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            f.write(f"Total lines processed: {self.stats['total_lines']}\n")
            f.write(f"Unique IMSIs found: {self.stats['unique_ims']}\n")
            f.write(f"Duplicates removed: {self.stats['duplicates_removed']}\n\n")
            f.write("By Operator:\n")
            
            for operator, lines in operator_files.items():
                f.write(f"  {operator}: {len(lines)} unique devices\n")
    
    def upload_cleaned_files(self):
        """Upload cleaned files back to Google Drive"""
        print("\n☁️ Uploading cleaned files to Google Drive...")
        
        # Create a dated folder for cleaned data
        date_str = datetime.now().strftime("%Y%m%d")
        dest_folder = f"{GDRIVE_FOLDER}/Cleaned_{date_str}"
        os.system(f"rclone mkdir {dest_folder}")
        
        # Upload all cleaned files
        files_to_upload = [
            "MASTER_unique_imsi.txt",
            "STATISTICS.txt",
            "Telenor_unique.txt",
            "Zong_unique.txt", 
            "Ufone_unique.txt",
            "Jazz_unique.txt"
        ]
        
        for filename in files_to_upload:
            filepath = os.path.join(LOCAL_TEMP, filename)
            if os.path.exists(filepath):
                os.system(f"rclone copy {filepath} {dest_folder}/")
                print(f"  ✅ Uploaded: {filename}")
        
        print(f"\n✅ Cleaned files uploaded to: {dest_folder}")
        return dest_folder
    
    def cleanup(self):
        """Remove temporary files"""
        os.system(f"rm -rf {LOCAL_TEMP}")
        print("🧹 Temporary files cleaned up")
    
    def run(self):
        """Main execution"""
        print("="*70)
        print("🧹 IMSI DEDUPLICATOR - Google Drive")
        print("="*70)
        
        # Download files
        files = self.download_files()
        
        if not files:
            print("❌ No files found in Google Drive")
            return
        
        # Process and deduplicate
        self.process_files(files)
        
        # Show statistics
        print("\n📊 STATISTICS")
        print("-"*40)
        print(f"Total lines processed: {self.stats['total_lines']}")
        print(f"Unique IMSIs found: {self.stats['unique_ims']}")
        print(f"Duplicates removed: {self.stats['duplicates_removed']}")
        
        # Create cleaned files
        self.create_cleaned_files()
        
        # Upload back to Drive
        dest = self.upload_cleaned_files()
        
        # Cleanup
        self.cleanup()
        
        print("\n" + "="*70)
        print(f"✅ COMPLETE! Cleaned files in: {dest}")
        print("="*70)
        
        # Show summary
        print("\n📁 Your friend can now access:")
        print(f"   - MASTER_unique_imsi.txt (all unique IMSIs)")
        print(f"   - STATISTICS.txt (summary)")
        print(f"   - [Operator]_unique.txt (per-operator files)")

if __name__ == "__main__":
    dedup = IMSIDeduplicator()
    dedup.run()
