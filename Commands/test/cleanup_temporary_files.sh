#!/bin/bash

# Execute this script from the Sparkle directory

#SBATCH --job-name=test/cleanup_temporary_files.sh
#SBATCH --output=TMP/cleanup_temporary_files.sh.txt
#SBATCH --error=TMP/cleanup_temporary_files.sh.err
#SBATCH --partition=graceADA
#SBATCH --mem-per-cpu=3gb
#SBATCH --exclude=
#SBATCH --ntasks=1
#SBATCH --nodes=1

# Activate environment
source activate sparkle_test &> /dev/null

# Initialise
Commands/initialise.py > /dev/null

# Cleanup temporary files
output_true="c Temporary files cleaned!"
output=$(Commands/cleanup_temporary_files.py | tail -1)

if [[ $output == $output_true ]];
then
	echo "[success] cleanup_temporary_files test succeeded"
else
	echo "[failure] cleanup_temporary_files test failed with output:"
	echo $output
fi

