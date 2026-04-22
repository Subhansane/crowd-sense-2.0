#!/bin/bash
# Run CrowdSense integration with IMSI catcher

# Activate virtual environment
cd ~/IMSI-catcher-master
source crowd_sense_env/bin/activate

echo "🚀 Starting CrowdSense Integration..."
echo "====================================="

# Run the integration script
python3 crowd_sense_integration.py

# Deactivate on exit
deactivate
