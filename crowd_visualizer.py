#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import datetime
import re
from collections import defaultdict

# Your data from the graphs
confirmed = {'Telenor': 312, 'Ufone': 3, 'Zong': 8, 'Jazz': 0}
signal_hits = {'Telenor': 354, 'Ufone': 8, 'Zong': 45, 'Jazz': 12}  # estimated

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Plot 1: Confirmed IMSIs
networks = list(confirmed.keys())
values = list(confirmed.values())
colors = ['purple', 'yellow', 'red', 'blue']
bars1 = ax1.bar(networks, values, color=colors)
ax1.set_title(f'Confirmed IMSI Users (Total: {sum(values)})')
ax1.set_ylabel('Number of Users')
for bar in bars1:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}', ha='center', va='bottom')

# Plot 2: Signal Hits
values2 = [signal_hits[n] for n in networks]
bars2 = ax2.bar(networks, values2, color=colors, alpha=0.7)
ax2.set_title(f'Signal Detections (Total: {sum(values2)})')
ax2.set_ylabel('Signal Bursts')
for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}', ha='center', va='bottom')

plt.tight_layout()
plt.savefig('crowd_summary.png')
plt.show()

