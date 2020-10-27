#!/bin/bash

# Execute this script from the Sparkle directory

#SBATCH --job-name=test/run_status.sh
#SBATCH --output=TMP/run_status.sh.txt
#SBATCH --error=TMP/run_status.sh.err
#SBATCH --partition=graceADA
#SBATCH --mem-per-cpu=3gb
#SBATCH --exclude=
#SBATCH --ntasks=1
#SBATCH --nodes=1

# Activate environment
source activate sparkle_test &> /dev/null

# System status
output_true="c Current running status of Sparkle reported!"
output=$(Commands/run_status.py | tail -1)

if [[ $output == $output_true ]];
then
	echo "[success] run_status test succeeded"
else
	echo "[failure] run_status test failed with output:"
	echo $output
fi

