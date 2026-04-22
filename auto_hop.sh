#!/bin/bash
FREQUENCIES=(
    "952.2M"
    "947.8M"
    "944.8M"
    "948.6M"
    "949.4M"
    "950.0M"
)
DWELL_TIME=45
echo "Auto Frequency Hopper Starting"
echo "Found ${#FREQUENCIES[@]} frequencies to monitor"
while true; do
    for FREQ in "${FREQUENCIES[@]}"; do
        echo "$(date): Switching to frequency: $FREQ"
        sudo pkill -f grgsm_livemon
        sleep 2
        echo "Starting grgsm_livemon on $FREQ"
        grgsm_livemon -f $FREQ &
        echo "Listening for $DWELL_TIME seconds..."
        sleep $DWELL_TIME
    done
done
