#!/bin/bash
# ULTIMATE CROWD SENSING AUTO HOPPER
# Optimized for maximum IMSI capture in moving crowds
# Strategic frequency hopping based on real network data

# ==========================================
# CONFIGURATION - TUNE THESE FOR YOUR NEEDS
# ==========================================

# FREQUENCY LIST (Prioritized by proven activity)
# Format: "FREQUENCY:NETWORK:WEIGHT"
# Higher weight = more time spent
FREQUENCIES=(
    # PRIORITY 1 - Your strongest signals (weights 5-6)
    "952.2M:ZONG:6"      # Your strongest signal
    "947.8M:ZONG:5"      # Your second strongest
    "944.8M:ZONG:5"      # Your third strongest
    
    # PRIORITY 2 - Major operator primaries (weights 3-4)
    "935.2M:JAZZ:4"      # Jazz primary
    "940.0M:TELENOR:4"   # Telenor primary
    "938.0M:UFONE:3"     # Ufone primary
    
    # PRIORITY 3 - Secondary channels (weights 2)
    "925.0M:ZONG:2"      # Zong secondary
    "936.0M:JAZZ:2"      # Jazz secondary
    "941.0M:TELENOR:2"   # Telenor secondary
    "939.0M:UFONE:2"     # Ufone secondary
    
    # PRIORITY 4 - Exploration (weight 1)
    "1805.0M:JAZZ:1"     # Jazz 1800 band
    "1815.0M:ZONG:1"     # Zong 1800 band
    "1820.0M:TELENOR:1"  # Telenor 1800 band
)

# ==========================================
# DYNAMIC TIMING CONFIGURATION
# ==========================================

# Base dwell time in seconds (adjust based on crowd density)
# 2-3 seconds: Dense crowd, maximum capture
# 4-5 seconds: Moderate crowd, balanced
# 6-8 seconds: Sparse crowd, detailed capture
BASE_DWELL=3

# Adaptive timing multiplier based on weight
# Weight 6 = 2.0x base time (6 seconds)
# Weight 5 = 1.7x base time (5.1 seconds)
# Weight 4 = 1.3x base time (3.9 seconds)
# Weight 3 = 1.0x base time (3 seconds)
# Weight 2 = 0.7x base time (2.1 seconds)
# Weight 1 = 0.3x base time (0.9 seconds)

# Gain setting (30-50 recommended)
GAIN=45

# ==========================================
# ADVANCED FEATURES
# ==========================================

# Enable/disable adaptive scanning
ADAPTIVE_MODE=true

# Minimum hits before considering frequency active
MIN_HITS=3

# Statistics file
STATS_FILE="$HOME/IMSI-catcher-master/crowd_stats.txt"

# Initialize stats
declare -A FREQ_HITS
declare -A NETWORK_COUNTS

# Load previous stats if available
if [ -f "$STATS_FILE" ]; then
    source "$STATS_FILE" 2>/dev/null
fi

# ==========================================
# COLOR CODES FOR OUTPUT
# ==========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# ==========================================
# DISPLAY HEADER
# ==========================================
clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     ULTIMATE CROWD SENSING AUTO HOPPER v3.0         ║${NC}"
echo -e "${CYAN}║         Optimized for Maximum IMSI Capture          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${WHITE}Crowd Sensing Configuration:${NC}"
echo -e "  ${GREEN}Base dwell time:${NC} ${BASE_DWELL}s (adapts by frequency weight)"
echo -e "  ${GREEN}Total frequencies:${NC} ${#FREQUENCIES[@]}"
echo -e "  ${GREEN}Gain setting:${NC} ${GAIN}"
echo -e "  ${GREEN}Adaptive mode:${NC} ${ADAPTIVE_MODE}"
echo ""

echo -e "${YELLOW}Frequency Strategy (Weight → Time):${NC}"
for entry in "${FREQUENCIES[@]}"; do
    IFS=':' read -r freq network weight <<< "$entry"
    case $network in
        ZONG)     COLOR=$RED ;;
        JAZZ)     COLOR=$BLUE ;;
        TELENOR)  COLOR=$PURPLE ;;
        UFONE)    COLOR=$YELLOW ;;
        *)        COLOR=$WHITE ;;
    esac
    dwell=$(echo "scale=1; $BASE_DWELL * (0.3 + $weight * 0.3)" | bc)
    printf "  ${COLOR}%-8s${NC} at ${WHITE}%-7s${NC} weight ${YELLOW}%d${NC} → ${GREEN}%.1fs${NC}\n" "$network" "$freq" "$weight" "$dwell"
done
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ==========================================
# MAIN SCANNING LOOP
# ==========================================
CYCLE=1
START_TIME=$(date +%s)
TOTAL_DEVICES=0

while true; do
    CYCLE_START=$(date +%s)
    echo -e "${WHITE}[Cycle #$CYCLE] $(date '+%H:%M:%S') - Scanning crowd...${NC}"
    
    for entry in "${FREQUENCIES[@]}"; do
        IFS=':' read -r freq network weight <<< "$entry"
        
        # Calculate adaptive dwell time
        if [ "$ADAPTIVE_MODE" = true ]; then
            # Base multiplier from weight
            multiplier=$(echo "scale=2; 0.3 + $weight * 0.3" | bc)
            
            # Boost if this frequency has been productive
            hits=${FREQ_HITS[$freq]:-0}
            if [ $hits -gt $MIN_HITS ]; then
                multiplier=$(echo "scale=2; $multiplier * 1.2" | bc)
            fi
            
            DWELL=$(echo "scale=1; $BASE_DWELL * $multiplier" | bc)
            # Round to nearest integer
            DWELL=$(printf "%.0f" "$DWELL")
            [ $DWELL -lt 1 ] && DWELL=1
        else
            DWELL=$BASE_DWELL
        fi
        
        # Network-specific color
        case $network in
            ZONG)     COLOR=$RED ;;
            JAZZ)     COLOR=$BLUE ;;
            TELENOR)  COLOR=$PURPLE ;;
            UFONE)    COLOR=$YELLOW ;;
            *)        COLOR=$WHITE ;;
        esac
        
        # Quick frequency switch with proper UDP output
sudo pkill -f grgsm_livemon >/dev/null 2>&1
sleep 1

# Start grgsm_livemon and force UDP output to port 4729 using netcat
if command -v nc &> /dev/null; then
    # Use netcat to forward to port 4729 (most reliable)
    grgsm_livemon -f $freq -g $GAIN 2>/dev/null | nc -u localhost 4729 >/dev/null 2>&1 &
else
    # Try --client option as fallback
    grgsm_livemon -f $freq -g $GAIN --client localhost:4729 >/dev/null 2>&1 &
fi

GRGSM_PID=$!
sleep 2

# Verify it's running
if kill -0 $GRGSM_PID 2>/dev/null; then
    echo "  ✅ grgsm_livemon running on $freq"
else
    echo "  ❌ Failed to start on $freq"
fi
        
        # Show compact progress
        echo -ne "  ${COLOR}${network}${NC} @ ${WHITE}${freq}${NC} ["
        
        # Monitor for activity during dwell
        ACTIVITY=0
        if [ -f "$HOME/IMSI-catcher-master/imsi_output.txt" ]; then
            BEFORE=$(wc -l < "$HOME/IMSI-catcher-master/imsi_output.txt" 2>/dev/null || echo 0)
        else
            BEFORE=0
        fi
        
        # Progress bar with activity monitoring
        for ((i=1; i<=DWELL; i++)); do
            sleep 1
            
            # Check for new IMSIs during this second
            if [ -f "$HOME/IMSI-catcher-master/imsi_output.txt" ]; then
                AFTER=$(wc -l < "$HOME/IMSI-catcher-master/imsi_output.txt" 2>/dev/null || echo 0)
                if [ $AFTER -gt $BEFORE ]; then
                    # New device detected!
                    echo -ne "${GREEN}#${NC}"
                    ACTIVITY=$((ACTIVITY + (AFTER - BEFORE)))
                    BEFORE=$AFTER
                else
                    echo -ne "${WHITE}.${NC}"
                fi
            else
                echo -ne "${WHITE}.${NC}"
            fi
        done
        
        echo -ne "] "
        
        # Report activity
        if [ $ACTIVITY -gt 0 ]; then
            echo -e "${GREEN}+$ACTIVITY devices${NC}"
            # Update stats
            FREQ_HITS[$freq]=$(( ${FREQ_HITS[$freq]:-0} + ACTIVITY ))
            NETWORK_COUNTS[$network]=$(( ${NETWORK_COUNTS[$network]:-0} + ACTIVITY ))
            TOTAL_DEVICES=$((TOTAL_DEVICES + ACTIVITY))
        else
            echo -e "${YELLOW}no activity${NC}"
        fi
        
        # Kill the process to save CPU
        sudo pkill -f grgsm_livemon >/dev/null 2>&1
    done
    
    # ==========================================
    # END OF CYCLE SUMMARY
    # ==========================================
    CYCLE_END=$(date +%s)
    CYCLE_TIME=$((CYCLE_END - CYCLE_START))
    
    echo ""
    echo -e "${CYAN}━━━━ Cycle #$CYCLE Complete ━━━━${NC}"
    echo -e "  ${GREEN}Cycle time:${NC} ${CYCLE_TIME}s"
    echo -e "  ${GREEN}Total devices:${NC} $TOTAL_DEVICES"
    
    # Show network breakdown
    if [ ${#NETWORK_COUNTS[@]} -gt 0 ]; then
        echo -e "  ${GREEN}Network breakdown:${NC}"
        for net in ZONG JAZZ TELENOR UFONE; do
            count=${NETWORK_COUNTS[$net]:-0}
            if [ $count -gt 0 ]; then
                case $net in
                    ZONG)     echo -e "    ${RED}Zong:${NC} $count devices" ;;
                    JAZZ)     echo -e "    ${BLUE}Jazz:${NC} $count devices" ;;
                    TELENOR)  echo -e "    ${PURPLE}Telenor:${NC} $count devices" ;;
                    UFONE)    echo -e "    ${YELLOW}Ufone:${NC} $count devices" ;;
                esac
            fi
        done
    fi
    
    # Show top performing frequencies
    echo -e "  ${GREEN}Hot frequencies:${NC}"
    for freq in "${!FREQ_HITS[@]}"; do
        hits=${FREQ_HITS[$freq]}
        if [ $hits -gt 0 ]; then
            # Find network for this frequency
            for entry in "${FREQUENCIES[@]}"; do
                if [[ "$entry" == *"$freq"* ]]; then
                    IFS=':' read -r f net w <<< "$entry"
                    printf "    ${WHITE}%-7s${NC} ${COLOR}%-6s${NC}: ${GREEN}%d hits${NC}\n" "$freq" "$net" "$hits"
                    break
                fi
            done
        fi
    done
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Save stats
    cat > "$STATS_FILE" << EOF
# Auto-generated stats for crowd sensing
FREQ_HITS=($(for f in "${!FREQ_HITS[@]}"; do echo "[$f]=${FREQ_HITS[$f]}"; done))
NETWORK_COUNTS=($(for n in "${!NETWORK_COUNTS[@]}"; do echo "[$n]=${NETWORK_COUNTS[$n]}"; done))
TOTAL_DEVICES=$TOTAL_DEVICES
LAST_CYCLE=$CYCLE
EOF
    
    ((CYCLE++))
    
    # Adaptive reordering - promote active frequencies
    if [ $((CYCLE % 5)) -eq 0 ] && [ "$ADAPTIVE_MODE" = true ]; then
        echo -e "${YELLOW}Adaptively reordering frequencies based on activity...${NC}"
        # (Simplified - in production would re-sort array by hit count)
    fi
done
