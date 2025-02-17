#!/bin/bash

# Import utils
. CLI/test/utils.sh

# Execute this script from the Sparkle directory

#SBATCH --job-name=test/compute_features.sh
#SBATCH --output=Tmp/compute_features.sh.txt
#SBATCH --error=Tmp/compute_features.sh.err
#SBATCH --mem-per-cpu=3gb
#SBATCH --exclude=
#SBATCH --ntasks=1
#SBATCH --nodes=1

# Settings
sparkle_test_settings_path="CLI/test/test_files/sparkle_settings.ini"
slurm_true="slurm"
slurm_available=$(detect_slurm)

# Prepare for test
instances_path="Examples/Resources/Instances/PTN"
extractor_path="Examples/Resources/Extractors/SAT-features-competition2012_revised_without_SatELite_sparkle"

CLI/initialise.py > /dev/null
CLI/add_instances.py $instances_path > /dev/null
CLI/add_feature_extractor.py $extractor_path > /dev/null

# Compute features
output_true="Computing features done!"
output=$(CLI/compute_features.py --settings-file $sparkle_test_settings_path | tail -1)

if [[ $output == $output_true ]];
then
	echo "[success] compute_features test succeeded"
else              
	echo "[failure] compute_features test failed with output:"
	echo $output
fi

# Compute features parallel
output_true="RunRunner Submitted a run to Slurm "
if ! [[ $slurm_available =~ "${slurm_true}" ]];
then
	output_true="Computing Features in parallel done!"
fi

output=$(CLI/compute_features.py --settings-file $sparkle_test_settings_path --parallel --recompute --run-on $slurm_available | tail -1)

if [[ $output =~ "${output_true}" ]];
then
	echo "[success] ($slurm_available) compute_features --parallel test succeeded"
    jobid=${output//[^0-9]/}

	if [[ $slurm_available =~ "${slurm_true}" ]];
	then
		scancel $jobid
	fi
else              
	echo "[failure] ($slurm_available) compute_features --parallel test failed with output:"
	echo $output
	if [[ $slurm_available =~ "${slurm_true}" ]];
	then
		kill_started_jobs_slurm
	fi
fi
