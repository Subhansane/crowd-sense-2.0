#!/bin/bash
# STABLE Xterm Launcher - Using crash-proof auto hopper

IMSI_PATH="/home/$USER/IMSI-catcher-master"
cd $IMSI_PATH

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   STABLE IMSI CATCHER LAUNCHER        ${NC}"
echo -e "${GREEN}   (No crashes - Fixed Auto Hopper)    ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Kill all existing processes
echo -e "${YELLOW}Cleaning up old processes...${NC}"
pkill -f grgsm_livemon 2>/dev/null
pkill -f imsi_catcher_fixed 2>/dev/null
pkill -f auto_hop_stable 2>/dev/null
pkill -f ai_logger 2>/dev/null
pkill -f simple_radar 2>/dev/null
sleep 2

# Create necessary directories
mkdir -p "$IMSI_PATH/imsi_ai_data"
mkdir -p "$IMSI_PATH/imsi_ai_data/$(date +%Y%m%d)"
touch "$IMSI_PATH/imsi_output.txt"

# ==========================================
# START STABLE AUTO HOPPER IN BACKGROUND
# ==========================================
echo -e "${BLUE}Starting STABLE Auto Hopper in background...${NC}"
chmod +x auto_hop_stable.sh
nohup ./auto_hop_stable.sh > /dev/null 2>&1 &
HOPPER_PID=$!
sleep 3

if ps -p $HOPPER_PID > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Auto Hopper running (PID: $HOPPER_PID)${NC}"
else
    echo -e "  ${RED}❌ Auto Hopper failed to start${NC}"
fi
echo ""

# ==========================================
# LAUNCH TERMINAL WINDOWS
# ==========================================

# Terminal 1: IMSI Catcher
echo -e "${BLUE}Opening IMSI Catcher...${NC}"
xterm -geometry 90x20+0+0 -T "📡 IMSI Catcher" -fa 'Monospace' -fs 10 -e bash -c "
    cd $IMSI_PATH
    echo -e '\\033[1;33m=== IMSI CATCHER ===\\033[0m'
    echo ''
    python3 imsi_catcher_fixed.py --txt imsi_output.txt
    echo ''
    echo 'Press any key to close...'
    read -n1
" &
sleep 2

# Terminal 2: Radar
echo -e "${BLUE}Opening Radar...${NC}"
xterm -geometry 100x30+700+0 -T "🖥️ IMSI Radar" -fa 'Monospace' -fs 9 -e bash -c "
    cd $IMSI_PATH
    echo -e '\\033[1;34m=== IMSI RADAR ===\\033[0m'
    echo ''
    echo -e '\\033[1;32mNetwork Legend:\\033[0m'
    echo '  • \\033[1;34mJAZZ\\033[0m    - Blue'
    echo '  • \\033[1;31mZONG\\033[0m    - Red'
    echo '  • \\033[1;35mTELENOR\\033[0m - Purple'
    echo '  • \\033[1;33mUFONE\\033[0m   - Yellow'
    echo ''
    python3 simple_radar.py
    echo ''
    echo 'Press any key to close...'
    read -n1
" &
sleep 2

# Terminal 3: AI Logger
echo -e "${BLUE}Opening AI Logger...${NC}"
xterm -geometry 90x20+0+400 -T "🤖 AI Logger" -fa 'Monospace' -fs 10 -e bash -c "
    cd $IMSI_PATH
    echo -e '\\033[1;35m=== AI LOGGER ===\\033[0m'
    echo ''
    echo 'Creating files every 2 minutes'
    echo ''
    python3 imsi_ai_logger.py
    echo ''
    echo 'Press any key to close...'
    read -n1
" &

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ALL SYSTEMS RUNNING!                 ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Windows:${NC}"
echo -e "  ${BLUE}→ IMSI Catcher${NC} - Capturing data"
echo -e "  ${BLUE}→ IMSI Radar${NC}   - Visual display"
echo -e "  ${BLUE}→ AI Logger${NC}    - Creating files"
echo ""
echo -e "${GREEN}Auto Hopper:${NC}"
echo -e "  ✅ Running in background (PID: $HOPPER_PID)"
echo -e "  📁 Log file: $IMSI_PATH/hopper_stable.log"
echo ""
echo -e "${YELLOW}To stop everything:${NC}"
echo "  pkill -f 'grgsm|imsi_catcher|auto_hop_stable|ai_logger|radar'"
echo ""

