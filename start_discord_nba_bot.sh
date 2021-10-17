#! /bin/bash
source "$CONDA_PREFIX"/etc/profile.d/conda.sh
conda activate chibidinosbot
nohup python3 /home/ubuntu/chibidinosbot/discord_nba_bot.py > /tmp/out.txt 2>&1 </dev/null &