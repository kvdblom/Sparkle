#!/bin/bash

# Execute this script from the Sparkle directory

#SBATCH --job-name=test/compute_features_parallel.sh
#SBATCH --output=TMP/compute_features_parallel.sh.txt
#SBATCH --error=TMP/compute_features_parallel.sh.err
#SBATCH --partition=graceADA
#SBATCH --mem-per-cpu=3gb
#SBATCH --exclude=
#SBATCH --ntasks=1
#SBATCH --nodes=1

# Prepare for test
instances_path="Examples/Resources/Instances/SAT_test"
extractor_path="Examples/Resources/Extractors/SAT-features-competition2012_revised_without_SatELite_sparkle"

Commands/initialise.py > /dev/null
Commands/add_instances.py --run-solver-later --run-extractor-later $instances_path > /dev/null
Commands/add_feature_extractor.py --run-extractor-later $extractor_path > /dev/null

# Add instances
output_true="c Computing features in parallel ..."
output=$(Commands/compute_features_parallel.py | tail -1)

if [[ $output == $output_true ]];
then
	echo "[success] compute_features_parallel test succeeded"
else              
	echo "[failure] compute_features_parallel test failed with output:"
	echo $output
fi

