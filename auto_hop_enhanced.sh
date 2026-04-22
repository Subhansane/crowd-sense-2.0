#!/bin/bash
# Enhanced Auto Hopper for Multiple Network Detection
# Includes specific frequencies for Jazz, Zong, Telenor, Ufone

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Comprehensive frequency list with network mapping
# Format: "FREQUENCY:NETWORK:DESCRIPTION"
FREQUENCY_LIST=(
    # Jazz frequencies (MNC 01, 07)
    "935.2M:JAZZ:GSM900 Primary"
    "935.6M:JAZZ:GSM900 Secondary" 
    "936.0M:JAZZ:GSM900 Urban"
    "936.4M:JAZZ:GSM900 Rural"
    "936.8M:JAZZ:GSM900 Extended"
    "1805.2M:JAZZ:GSM1800 City Center"
    "1805.6M:JAZZ:GSM1800 Business District"
    "1810.0M:JAZZ:GSM1800 Suburban"
    
    # Zong frequencies (MNC 04)
    "925.0M:ZONG:GSM900 Primary"
    "925.4M:ZONG:GSM900 Secondary"
    "925.8M:ZONG:GSM900 Urban"
    "926.2M:ZONG:GSM900 Rural"
    "944.8M:ZONG:Strong Signal"  # Your captured frequency
    "947.8M:ZONG:Very Strong"    # Your captured frequency
    "952.2M:ZONG:Strongest"      # Your captured frequency
    "1815.0M:ZONG:GSM1800"
    
    # Telenor frequencies (MNC 06)
    "940.0M:TELENOR:GSM900 Primary"
    "940.4M:TELENOR:GSM900 Secondary"
    "940.8M:TELENOR:GSM900 Urban"
    "941.2M:TELENOR:GSM900 Rural"
    "948.6M:TELENOR:Good Signal"  # Your captured frequency
    "949.4M:TELENOR:Good Signal"  # Your captured frequency
    "950.0M:TELENOR:Good Signal"  # Your captured frequency
    "1820.0M:TELENOR:GSM1800"
    
    # Ufone frequencies (MNC 03)
    "938.0M:UFONE:GSM900 Primary"
    "938.4M:UFONE:GSM900 Secondary"
    "938.8M:UFONE:GSM900 Urban"
    "939.2M:UFONE:GSM900 Rural"
    "1825.0M:UFONE:GSM1800"
    
    # Foreign/International frequencies (may appear near borders/airports)
    "935.0M:FOREIGN:Possible Indian Operator"
    "940.2M:FOREIGN:Possible Afghan Operator"
    "945.0M:FOREIGN:Possible Iranian Operator"
)

# Time to spend on each frequency (seconds)
# Shorter time for known frequencies, longer for new discoveries
DWELL_TIME=30

# Statistics tracking
declare -A network_count
declare -A frequency_hits

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ENHANCED NETWORK DETECTOR v2.0      ${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Scanning ${#FREQUENCY_LIST[@]} frequencies across 5 networks${NC}"
echo -e "${BLUE}Jazz, Zong, Telenor, Ufone, Foreign${NC}"
echo ""

# Group frequencies by network for summary
for entry in "${FREQUENCY_LIST[@]}"; do
    IFS=':' read -r freq network desc <<< "$entry"
    network_count[$network]=$((network_count[$network] + 1))
done

echo -e "${GREEN}Frequency distribution by network:${NC}"
for network in "${!network_count[@]}"; do
    case $network in
        JAZZ)    echo -e "  ${BLUE}Jazz: ${network_count[$network]} frequencies${NC}" ;;
        ZONG)    echo -e "  ${RED}Zong: ${network_count[$network]} frequencies${NC}" ;;
        TELENOR) echo -e "  ${PURPLE}Telenor: ${network_count[$network]} frequencies${NC}" ;;
        UFONE)   echo -e "  ${YELLOW}Ufone: ${network_count[$network]} frequencies${NC}" ;;
        FOREIGN) echo -e "  ${GREEN}Foreign: ${network_count[$network]} frequencies${NC}" ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo ""

# Main scanning loop
CYCLE=1
while true; do
    echo -e "${YELLOW}=== Starting Scan Cycle #$CYCLE at $(date) ===${NC}"
    
    for entry in "${FREQUENCY_LIST[@]}"; do
        IFS=':' read -r freq network desc <<< "$entry"
        
        # Color code by network
        case $network in
            JAZZ)    COLOR=$BLUE ;;
            ZONG)    COLOR=$RED ;;
            TELENOR) COLOR=$PURPLE ;;
            UFONE)   COLOR=$YELLOW ;;
            FOREIGN) COLOR=$GREEN ;;
            *)       COLOR=$NC ;;
        esac
        
        echo -e "${COLOR}[$(date +%H:%M:%S)] → Switching to: $freq ($network - $desc)${NC}"
        
        # Kill existing grgsm_livemon
        sudo pkill -f grgsm_livemon >/dev/null 2>&1
        sleep 2
        
        # Start with gain adjustment for better reception
        echo "  Starting grgsm_livemon on $freq with gain 40"
        grgsm_livemon -f $freq -g 40 >/dev/null 2>&1 &
        
        # Show progress bar
        echo -n "  Listening: "
        for ((i=0; i<$DWELL_TIME; i+=5)); do
            echo -n "█"
            sleep 5
            
            # Quick check if any data is being received
            if [ $((i % 10)) -eq 0 ]; then
                # Check if imsi_output.txt was updated
                if [ -f ~/IMSI-catcher-master/imsi_output.txt ]; then
                    recent=$(tail -1 ~/IMSI-catcher-master/imsi_output.txt 2>/dev/null | grep -c "$freq")
                    if [ $recent -gt 0 ]; then
                        frequency_hits[$freq]=$((frequency_hits[$freq] + 1))
                        echo -n "!"
                    fi
                fi
            fi
        done
        echo " Done!"
        
        # Stop the process
        sudo pkill -f grgsm_livemon >/dev/null 2>&1
    done
    
    # End of cycle summary
    echo -e "\n${GREEN}=== Cycle #$CYCLE Complete at $(date) ===${NC}"
    
    # Show hit statistics
    if [ ${#frequency_hits[@]} -gt 0 ]; then
        echo -e "${YELLOW}Frequencies with activity detected:${NC}"
        for freq in "${!frequency_hits[@]}"; do
            echo "  $freq: ${frequency_hits[$freq]} hits"
        done
    else
        echo -e "${RED}No activity detected in this cycle${NC}"
    fi
    
    echo -e "${GREEN}========================================${NC}\n"
    ((CYCLE++))
done
