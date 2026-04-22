#!/bin/bash
# MINIMAL LAUNCHER - Auto Hopper runs silently in background
# Only shows IMSI Catcher, Radar, and AI Logger windows

IMSI_PATH="/home/$USER/IMSI-catcher-master"
cd $IMSI_PATH

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   MINIMAL IMSI CATCHER LAUNCHER       ${NC}"
echo -e "${GREEN}   (Auto Hopper runs in background)    ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Kill any existing processes
echo -e "${YELLOW}Cleaning up old processes...${NC}"
pkill -f grgsm_livemon 2>/dev/null
pkill -f imsi_catcher_fixed 2>/dev/null
pkill -f auto_hop_crowd_ultimate 2>/dev/null
pkill -f ai_logger 2>/dev/null
pkill -f simple_radar 2>/dev/null
sleep 2

# Create necessary directories
mkdir -p "$IMSI_PATH/imsi_ai_data"
mkdir -p "$IMSI_PATH/imsi_ai_data/$(date +%Y%m%d)"
touch "$IMSI_PATH/imsi_output.txt"

# ==========================================
# START AUTO HOPPER IN BACKGROUND (NO WINDOW)
# ==========================================
echo -e "${BLUE}Starting Auto Hopper in background...${NC}"

# Use full path and ensure it's executable
AUTO_HOPPER="$IMSI_PATH/auto_hop_crowd_ultimate.sh"
if [ ! -f "$AUTO_HOPPER" ]; then
    echo -e "${RED}Error: Auto hopper not found at $AUTO_HOPPER${NC}"
    exit 1
fi

# Make sure it's executable
chmod +x "$AUTO_HOPPER"

# Start with nohup and log output to file for debugging
nohup "$AUTO_HOPPER" > "$IMSI_PATH/auto_hopper.log" 2>&1 &
AUTO_HOPPER_PID=$!

# Verify it started
sleep 2
if ps -p $AUTO_HOPPER_PID > /dev/null; then
    echo -e "  ${GREEN}✅ Auto Hopper running (PID: $AUTO_HOPPER_PID)${NC}"
    echo -e "  ${YELLOW}→ Log file: $IMSI_PATH/auto_hopper.log${NC}"
else
    echo -e "  ${RED}❌ Auto Hopper failed to start${NC}"
    echo -e "  ${YELLOW}Check log: $IMSI_PATH/auto_hopper.log${NC}"
fi
echo ""
# ==========================================
# LAUNCH TERMINAL WINDOWS
# ==========================================

# Terminal 1: IMSI Catcher
echo -e "${BLUE}Opening IMSI Catcher...${NC}"
xterm -geometry 90x20+0+0 -T "📡 IMSI Catcher" -fa 'Monospace' -fs 10 -e bash -c "
    echo -e '\\033[1;33m=== IMSI CATCHER ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m✅ Capturing IMSI Data\\033[0m'
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

# Terminal 2: Radar
echo -e "${BLUE}Opening Radar...${NC}"
xterm -geometry 100x30+700+0 -T "🖥️ IMSI Radar" -fa 'Monospace' -fs 9 -e bash -c "
    echo -e '\\033[1;34m=== IMSI RADAR ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m📊 Network Color Legend:\\033[0m'
    echo '  • \\033[1;34mJAZZ\\033[0m    - Blue'
    echo '  • \\033[1;31mZONG\\033[0m    - Red'
    echo '  • \\033[1;35mTELENOR\\033[0m - Purple'
    echo '  • \\033[1;33mUFONE\\033[0m   - Yellow'
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

# Terminal 3: AI Logger
echo -e "${BLUE}Opening AI Logger...${NC}"
xterm -geometry 90x20+0+400 -T "🤖 AI Logger" -fa 'Monospace' -fs 10 -e bash -c "
    echo -e '\\033[1;35m=== AI LOGGER ===\\033[0m'
    echo ''
    echo -e '\\033[1;32m✅ Creating files every 2 minutes\\033[0m'
    echo ''
    echo '📁 Output: imsi_ai_data/\$(date +%Y%m%d)/'
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

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ALL SYSTEMS RUNNING!                 ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Active Windows:${NC}"
echo -e "  ${BLUE}→ IMSI Catcher${NC} - Capturing data"
echo -e "  ${BLUE}→ IMSI Radar${NC}   - Visual display"
echo -e "  ${BLUE}→ AI Logger${NC}    - Creating files"
echo ""
echo -e "${GREEN}Auto Hopper Status:${NC}"
echo -e "  ✅ Running in background (PID: $AUTO_HOPPER_PID)"
echo -e "  🔇 No window - completely silent"
echo ""
echo -e "${YELLOW}To stop everything:${NC}"
echo "  pkill -f grgsm_livemon"
echo "  pkill -f imsi_catcher_fixed"
echo "  pkill -f auto_hop_crowd_ultimate"
echo "  pkill -f ai_logger"
echo "  pkill -f simple_radar"
echo ""
echo -e "${GREEN}Or run this one-liner:${NC}"
echo "  pkill -f 'grgsm|imsi_catcher|auto_hop|ai_logger|radar'"
echo ""
