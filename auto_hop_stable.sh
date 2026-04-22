#!/bin/bash
# STABLE Auto Hopper - No crashes, optimized for continuous operation

# ==========================================
# CONFIGURATION
# ==========================================

# Frequencies with network mapping
FREQUENCIES=(
    "952.2M:ZONG"
    "947.8M:ZONG"
    "944.8M:ZONG"
    "935.2M:JAZZ"
    "940.0M:TELENOR"
    "938.0M:UFONE"
    "925.0M:ZONG"
    "936.0M:JAZZ"
    "941.0M:TELENOR"
    "939.0M:UFONE"
)

# Gain setting (30-50 recommended)
GAIN=40

# Dwell time per frequency (seconds)
DWELL=5

# Log file
LOG_FILE="$HOME/IMSI-catcher-master/hopper_stable.log"

# ==========================================
# COLOR CODES
# ==========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# ==========================================
# FUNCTIONS
# ==========================================

cleanup() {
    echo -e "\n${YELLOW}Shutting down Auto Hopper...${NC}"
    sudo pkill -9 -f grgsm_livemon 2>/dev/null
    echo -e "${GREEN}Cleanup complete${NC}"
    exit 0
}

# Set trap for Ctrl+C
trap cleanup SIGINT SIGTERM

# ==========================================
# MAIN
# ==========================================

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   STABLE AUTO HOPPER v1.0             ${NC}"
echo -e "${GREEN}   No crashes - Optimized              ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  ${BLUE}Frequencies:${NC} ${#FREQUENCIES[@]}"
echo -e "  ${BLUE}Gain:${NC} $GAIN"
echo -e "  ${BLUE}Dwell time:${NC} ${DWELL}s per frequency"
echo -e "  ${BLUE}Log file:${NC} $LOG_FILE"
echo ""

echo -e "${GREEN}Starting main loop - Press Ctrl+C to stop${NC}"
echo ""

# Main loop
CYCLE=1
DEVICE_COUNT=0

while true; do
    echo -e "${YELLOW}[Cycle $CYCLE] $(date '+%H:%M:%S')${NC}"
    
    for entry in "${FREQUENCIES[@]}"; do
        IFS=':' read -r freq network <<< "$entry"
        
        # Color based on network
        case $network in
            ZONG)     COLOR=$RED ;;
            JAZZ)     COLOR=$BLUE ;;
            TELENOR)  COLOR=$PURPLE ;;
            UFONE)    COLOR=$YELLOW ;;
            *)        COLOR=$NC ;;
        esac
        
        # Kill any existing grgsm_livemon processes
        sudo pkill -9 -f grgsm_livemon >/dev/null 2>&1
        sleep 1
        
        # Start grgsm_livemon with output suppressed
        grgsm_livemon -f $freq -g $GAIN >/dev/null 2>&1 &
        PID=$!
        sleep 2
        
        # Check if it started successfully
        if kill -0 $PID 2>/dev/null; then
            echo -ne "  ${COLOR}${network}${NC} @ ${freq} ["
            
            # Monitor for device detection during dwell
            BEFORE=$(wc -l < ~/IMSI-catcher-master/imsi_output.txt 2>/dev/null || echo 0)
            
            # Progress bar
            for ((i=1; i<=DWELL; i++)); do
                echo -n "."
                sleep 1
            done
            
            # Check for new devices
            AFTER=$(wc -l < ~/IMSI-catcher-master/imsi_output.txt 2>/dev/null || echo 0)
            NEW=$((AFTER - BEFORE))
            
            if [ $NEW -gt 0 ]; then
                echo -e "] ${GREEN}+$NEW devices${NC}"
                DEVICE_COUNT=$((DEVICE_COUNT + NEW))
                
                # Log to file
                echo "$(date '+%Y-%m-%d %H:%M:%S') - $network @ $freq - $NEW new devices" >> "$LOG_FILE"
            else
                echo -e "] ${YELLOW}no activity${NC}"
            fi
            
            # Kill the process to save CPU
            sudo kill -9 $PID 2>/dev/null
            sleep 1
        else
            echo -e "  ${RED}${network} @ ${freq} - FAILED TO START${NC}"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - $network @ $freq - FAILED" >> "$LOG_FILE"
        fi
    done
    
    # End of cycle summary
    echo -e "${GREEN}━━━━ Cycle $CYCLE complete ━━━━${NC}"
    echo -e "  Total devices captured: $DEVICE_COUNT"
    echo -e "  Check log: $LOG_FILE"
    echo ""
    
    ((CYCLE++))
done
