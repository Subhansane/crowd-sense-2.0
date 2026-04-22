#!/bin/bash
# Advanced IMSI Catcher Xterm Launcher with Enhanced Network Detection
# Includes Jazz, Zong, Telenor, Ufone specific frequencies

IMSI_PATH="/home/$USER/IMSI-catcher-master"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ADVANCED IMSI CATCHER SYSTEM        ${NC}"
echo -e "${CYAN}   Multi-Network Detection (Jazz/Zong/Telenor/Ufone)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

cd $IMSI_PATH

# Kill any existing processes
pkill -f grgsm_livemon 2>/dev/null
pkill -f imsi_catcher_fixed 2>/dev/null
pkill -f auto_hop_enhanced 2>/dev/null
pkill -f ai_logger 2>/dev/null
pkill -f simple_radar 2>/dev/null
sleep 2

echo -e "${GREEN}Opening 5 xterm windows with advanced network detection...${NC}"
echo ""

# Terminal 1: Enhanced Auto Hopper (Top Left) - NEW VERSION
xterm -geometry 100x30+0+0 -T "🚀 Enhanced Auto Hopper" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;32m=== ENHANCED AUTO HOPPER - MULTI-NETWORK ===\\033[0m'
    echo ''
    echo -e '\\033[1;33mNetwork frequencies being scanned:\\033[0m'
    echo -e '  \\033[1;34mJAZZ\\033[0m    : 935.2M, 935.6M, 936.0M, 936.4M, 936.8M, 1805.2M, 1805.6M, 1810.0M'
    echo -e '  \\033[1;31mZONG\\033[0m    : 925.0M, 925.4M, 925.8M, 926.2M, 944.8M, 947.8M, 952.2M, 1815.0M'
    echo -e '  \\033[1;35mTELENOR\\033[0m : 940.0M, 940.4M, 940.8M, 941.2M, 948.6M, 949.4M, 950.0M, 1820.0M'
    echo -e '  \\033[1;33mUFONE\\033[0m   : 938.0M, 938.4M, 938.8M, 939.2M, 1825.0M'
    echo -e '  \\033[1;32mFOREIGN\\033[0m : 935.0M, 940.2M, 945.0M (near borders)'
    echo ''
    echo -e '\\033[1;33mStarting enhanced scanner in 3 seconds...\\033[0m'
    sleep 3
    cd $IMSI_PATH && ./auto_hop_enhanced.sh
    echo ''
    echo -e '\\033[1;31mEnhanced Auto Hopper Stopped\\033[0m'
    echo 'Press any key to close...'
    read -n1
" &

sleep 2

# Terminal 2: IMSI Catcher (Top Middle)
xterm -geometry 90x20+700+0 -T "📡 IMSI Catcher" -fa 'Monospace' -fs 10 -e bash -c "
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

# Terminal 3: Enhanced Radar with Network Colors (Middle Left)
xterm -geometry 100x30+0+350 -T "🖥️ Multi-Network Radar" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;34m=== MULTI-NETWORK RADAR DISPLAY ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m📊 Network Color Legend:\\033[0m'
    echo '  • \\033[1;34mJAZZ\\033[0m    - Blue bars'
    echo '  • \\033[1;31mZONG\\033[0m    - Red bars'
    echo '  • \\033[1;35mTELENOR\\033[0m - Purple bars'
    echo '  • \\033[1;33mUFONE\\033[0m   - Yellow bars'
    echo '  • \\033[1;32mFOREIGN\\033[0m - Green bars'
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

# Terminal 4: AI Logger (Middle Right)
xterm -geometry 90x20+700+350 -T "🤖 AI Logger" -fa 'Monospace' -fs 10 -e bash -c "
    echo -e '\\033[1;35m=== AI LOGGER - NETWORK DATA COLLECTOR ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m📁 Creating network-specific files every 2 minutes\\033[0m'
    echo ''
    echo 'Files organized by date in: imsi_ai_data/YYYYMMDD/'
    echo ''
    echo -e '\\033[1;33mStarting AI logger in 3 seconds...\\033[0m'
    sleep 3
    cd $IMSI_PATH
    python3 imsi_ai_logger.py
    echo ''
    echo -e '\\033[1;31mAI Logger Stopped\\033[0m'
    echo 'Press any key to close...'
    read -n1
" &

sleep 2

# Terminal 5: Live Network Monitor (Bottom - Full Width)
xterm -geometry 180x20+0+700 -T "📊 Live Network Monitor" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;36m=== LIVE MULTI-NETWORK MONITOR ===\\033[0m'
    echo ''
    echo -e '\\033[1;32mREAL-TIME IMSI DATA BY NETWORK:\\033[0m'
    echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
    echo ''
    cd $IMSI_PATH
    tail -f imsi_output.txt | while read line; do
        if echo \"\$line\" | grep -q \"Jazz\"; then
            echo -e \"\\033[1;34mJAZZ: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"Zong\"; then
            echo -e \"\\033[1;31mZONG: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"Telenor\"; then
            echo -e \"\\033[1;35mTELENOR: \\033[0m\$line\"
        elif echo \"\$line\" | grep -q \"Ufone\"; then
            echo -e \"\\033[1;33mUFONE: \\033[0m\$line\"
        else
            echo -e \"\\033[1;32mOTHER: \\033[0m\$line\"
        fi
    done
" &

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All 5 advanced terminals launched!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Terminal Windows:${NC}"
echo -e "  ${BLUE}Top Left:${NC}     🚀 Enhanced Auto Hopper ${GREEN}(NEW - Multi-Network)${NC}"
echo -e "  ${BLUE}Top Middle:${NC}   📡 IMSI Catcher"
echo -e "  ${BLUE}Middle Left:${NC}  🖥️ Multi-Network Radar ${GREEN}(Color-coded)${NC}"
echo -e "  ${BLUE}Middle Right:${NC} 🤖 AI Logger"
echo -e "  ${BLUE}Bottom:${NC}       📊 Live Network Monitor ${GREEN}(Color-coded)${NC}"
echo ""
echo -e "${CYAN}Network Detection Targets:${NC}"
echo -e "  • ${BLUE}JAZZ${NC}    - 8 frequencies (935-936MHz, 1805-1810MHz)"
echo -e "  • ${RED}ZONG${NC}    - 8 frequencies (925-926MHz, 944-952MHz, 1815MHz)"
echo -e "  • ${PURPLE}TELENOR${NC} - 8 frequencies (940-941MHz, 948-950MHz, 1820MHz)"
echo -e "  • ${YELLOW}UFONE${NC}   - 5 frequencies (938-939MHz, 1825MHz)"
echo ""
echo -e "${GREEN}To stop everything:${NC}"
echo "  pkill -f grgsm_livemon"
echo "  pkill -f imsi_catcher_fixed"
echo "  pkill -f auto_hop_enhanced"
echo "  pkill -f ai_logger"
echo "  pkill -f simple_radar"
echo ""

