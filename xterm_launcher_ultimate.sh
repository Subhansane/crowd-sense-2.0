#!/bin/bash
# ULTIMATE IMSI Catcher Xterm Launcher
# With Crowd Sensing Auto Hopper + Fixed AI Logger

IMSI_PATH="/home/$USER/IMSI-catcher-master"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     ULTIMATE IMSI CATCHER - CROWD SENSING EDITION   ║${NC}"
echo -e "${CYAN}║      Auto Hopper + Fixed AI Logger + Radar          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

cd $IMSI_PATH

# Kill any existing processes
pkill -f grgsm_livemon 2>/dev/null
pkill -f imsi_catcher_fixed 2>/dev/null
pkill -f auto_hop_crowd_ultimate 2>/dev/null
pkill -f ai_logger 2>/dev/null
pkill -f simple_radar 2>/dev/null

# Ensure AI logger directory exists
mkdir -p "$IMSI_PATH/imsi_ai_data"
mkdir -p "$IMSI_PATH/imsi_ai_data/$(date +%Y%m%d)"

# Clear old temp files but keep structure
> "$IMSI_PATH/imsi_output.txt" 2>/dev/null || touch "$IMSI_PATH/imsi_output.txt"

echo -e "${GREEN}Opening 5 xterm windows with Ultimate Crowd Sensing...${NC}"
echo ""
sleep 2

# Terminal 1: Ultimate Crowd Sensing Auto Hopper (Top Left)
xterm -geometry 110x35+0+0 -T "🚀 Ultimate Crowd Hopper" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;36m╔════════════════════════════════════════════════╗\\033[0m'
    echo -e '\\033[1;36m║     ULTIMATE CROWD SENSING AUTO HOPPER       ║\\033[0m'
    echo -e '\\033[1;36m╚════════════════════════════════════════════════╝\\033[0m'
    echo ''
    echo -e '\\033[1;33mCrowd Sensing Strategy:\\033[0m'
    echo '  • Weighted frequencies: More time on proven bands'
    echo '  • Adaptive timing: Boosts productive frequencies'
    echo '  • Real-time monitoring: See devices as they appear'
    echo '  • Network breakdown: Tracks Jazz, Zong, Telenor, Ufone'
    echo ''
    echo -e '\\033[1;32mFrequency Weights:\\033[0m'
    echo '  • 952.2M (ZONG)   - Weight 6 (6s) - Your strongest'
    echo '  • 947.8M (ZONG)   - Weight 5 (5s) - Very strong'
    echo '  • 944.8M (ZONG)   - Weight 5 (5s) - Very strong'
    echo '  • 935.2M (JAZZ)   - Weight 4 (4s) - Jazz primary'
    echo '  • 940.0M (TELENOR) - Weight 4 (4s) - Telenor primary'
    echo '  • 938.0M (UFONE)   - Weight 3 (3s) - Ufone primary'
    echo '  • +6 more frequencies with lower weights'
    echo ''
    echo -e '\\033[1;33mStarting Ultimate Crowd Hopper in 3 seconds...\\033[0m'
    sleep 3
    cd $IMSI_PATH && ./auto_hop_crowd_ultimate.sh
    echo ''
    echo -e '\\033[1;31mAuto Hopper Stopped\\033[0m'
    echo 'Press any key to close...'
    read -n1
" &

sleep 2

# Terminal 2: IMSI Catcher (Top Middle)
xterm -geometry 90x20+900+0 -T "📡 IMSI Catcher" -fa 'Monospace' -fs 10 -e bash -c "
    echo -e '\\033[1;33m=== IMSI CATCHER - NO SUDO ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m✅ Capturing IMSI Data from all networks\\033[0m'
    echo ''
    echo 'Output saved to: imsi_output.txt'
    echo ''
    echo -e '\\033[1;33mStarting in 2 seconds...\\033[0m'
    sleep 2
    cd $IMSI_PATH
    python3 imsi_catcher_fixed.py --txt imsi_output.txt
    echo ''
    echo -e '\\033[1;31mIMSI Catcher Stopped\\033[0m'
    echo 'Press any key to close...'
    read -n1
" &

sleep 2

# Terminal 3: Multi-Network Radar (Middle Left)
xterm -geometry 100x30+0+400 -T "🖥️ Multi-Network Radar" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;34m=== MULTI-NETWORK RADAR DISPLAY ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m📊 Network Color Legend:\\033[0m'
    echo '  • \\033[1;34mJAZZ\\033[0m    - Blue bars'
    echo '  • \\033[1;31mZONG\\033[0m    - Red bars'
    echo '  • \\033[1;35mTELENOR\\033[0m - Purple bars'
    echo '  • \\033[1;33mUFONE\\033[0m   - Yellow bars'
    echo ''
    echo '📁 Reading from: imsi_output.txt'
    echo ''
    echo -e '\\033[1;33mStarting radar in 3 seconds...\\033[0m'
    sleep 3
    cd $IMSI_PATH
    python3 simple_radar.py
    echo ''
    echo -e '\\033[1;31mRadar Stopped\\033[0m'
    echo 'Press any key to close...'
    read -n1
" &

sleep 2

# Terminal 4: FIXED AI LOGGER - Creates REAL CSV files!
xterm -geometry 90x20+900+400 -T "🤖 AI Logger (CSV)" -fa 'Monospace' -fs 10 -e bash -c "
    echo -e '\\033[1;35m╔════════════════════════════════════════════╗\\033[0m'
    echo -e '\\033[1;35m║     FIXED AI LOGGER - CSV GENERATOR       ║\\033[0m'
    echo -e '\\033[1;35m╚════════════════════════════════════════════╝\\033[0m'
    echo ''
    echo -e '\\033[1;32m✅ Creating REAL CSV files every 2 minutes\\033[0m'
    echo ''
    echo '📁 Output directory: imsi_ai_data/\$(date +%Y%m%d)/'
    echo '📄 File format: imsi_YYYYMMDD_HHMMSS.csv'
    echo '📊 Data: timestamp, imsi, operator, mcc, mnc'
    echo ''
    echo -e '\\033[1;33mChecking for IMSI data...\\033[0m'
    cd $IMSI_PATH
    
    # Check if imsi_output.txt has data
    if [ -f imsi_output.txt ]; then
        SIZE=\$(wc -l < imsi_output.txt)
        echo -e \"\\033[1;32m  📊 imsi_output.txt has \$SIZE lines\\033[0m\"
    else
        echo -e \"\\033[1;31m  ⚠️ imsi_output.txt not found yet\\033[0m\"
    fi
    echo ''
    
    echo -e '\\033[1;33mStarting FIXED AI Logger in 3 seconds...\\033[0m'
    sleep 3
    
    # Run the FIXED AI logger (not the test version)
    python3 imsi_ai_logger_fixed.py
    echo ''
    echo -e '\\033[1;31mAI Logger Stopped\\033[0m'
    echo 'Press any key to close...'
    read -n1
" &
# Terminal 5: Live Network Monitor (Bottom - Full Width)
xterm -geometry 180x20+0+750 -T "📊 Live Network Monitor" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;36m=== LIVE MULTI-NETWORK MONITOR ===\\033[0m'
    echo ''
    echo -e '\\033[1;32mREAL-TIME IMSI DATA BY NETWORK:\\033[0m'
    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    echo ''
    cd $IMSI_PATH
    
    # Monitor with network color coding
    tail -f imsi_output.txt 2>/dev/null | while read line; do
        if echo \"\$line\" | grep -q \"Jazz\"; then
            echo -e \"\\033[1;34mJAZZ: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"Zong\"; then
            echo -e \"\\033[1;31mZONG: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"Telenor\"; then
            echo -e \"\\033[1;35mTELENOR: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"Ufone\"; then
            echo -e \"\\033[1;33mUFONE: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"410 0\"; then
            echo -e \"\\033[1;32mOTHER: \\033[0m\$line\"
        fi
    done
" &

echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ALL 5 ULTIMATE TERMINALS LAUNCHED!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Terminal Windows:${NC}"
echo -e "  ${BLUE}Top Left:${NC}     🚀 Ultimate Crowd Hopper ${GREEN}(Weighted scanning)${NC}"
echo -e "  ${BLUE}Top Middle:${NC}   📡 IMSI Catcher"
echo -e "  ${BLUE}Middle Left:${NC}  🖥️ Multi-Network Radar"
echo -e "  ${BLUE}Middle Right:${NC} 🤖 AI Logger ${RED}(FIXED - Creating files now!)${NC}"
echo -e "  ${BLUE}Bottom:${NC}       📊 Live Network Monitor"
echo ""

