#!/bin/bash
# Start all IMSI catcher components

echo "🚀 Starting IMSI Catcher System..."

# Terminal 1: IMSI Catcher
gnome-terminal -- bash -c "cd ~/IMSI-catcher-master && python3 imsi_catcher_fixed.py --txt imsi_output.txt; exec bash"

sleep 3

# Terminal 2: Auto Hopper
gnome-terminal -- bash -c "cd ~/IMSI-catcher-master && ./auto_hop_crowd_ultimate.sh; exec bash"

sleep 3

# Terminal 3: Radar (optional)
gnome-terminal -- bash -c "cd ~/IMSI-catcher-master && python3 simple_radar.py; exec bash"

sleep 3

# Terminal 4: InfinityFree Uploader
gnome-terminal -- bash -c "cd ~/IMSI-catcher-master && python3 infinity_uploader.py; exec bash"

echo "✅ All components started!"
echo "📡 IMSI Catcher is running"
echo "🔄 Auto Hopper is scanning"
echo "📊 Radar is displaying"
echo "☁️  Uploader is sending to InfinityFree"
