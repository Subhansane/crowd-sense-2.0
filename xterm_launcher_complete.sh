#!/bin/bash
IMSI_PATH="/home/$USER/IMSI-catcher-master"
cd $IMSI_PATH
pkill -f grgsm_livemon 2>/dev/null
pkill -f imsi_catcher_fixed 2>/dev/null
pkill -f auto_hop 2>/dev/null
pkill -f ai_logger 2>/dev/null
pkill -f simple_radar 2>/dev/null
sleep 2
xterm -geometry 90x20+0+0 -T "Auto Hopper" -e "cd $IMSI_PATH && ./auto_hop.sh; read -n1" &
sleep 2
xterm -geometry 90x20+700+0 -T "IMSI Catcher" -e "cd $IMSI_PATH && python3 imsi_catcher_fixed.py --txt imsi_output.txt; read -n1" &
sleep 2
xterm -geometry 100x30+0+350 -T "IMSI Radar" -e "cd $IMSI_PATH && python3 simple_radar.py; read -n1" &
sleep 2
xterm -geometry 90x20+700+350 -T "AI Logger" -e "cd $IMSI_PATH && python3 imsi_ai_logger.py; read -n1" &
sleep 2
xterm -geometry 180x20+0+700 -T "Live Monitor" -e "cd $IMSI_PATH && tail -f imsi_output.txt" &
echo "All terminals launched from $IMSI_PATH"
