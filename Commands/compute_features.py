#!/usr/bin/env python3
"""Sparkle command to compute features for instances."""

import sys
import argparse
from pathlib import Path

from sparkle_help import sparkle_global_help as sgh
from sparkle_help import sparkle_feature_data_csv_help as sfdcsv
from sparkle_help import sparkle_compute_features_help as scf
from sparkle_help import sparkle_job_parallel_help as sjph
from sparkle_help import sparkle_logging as sl
from sparkle_help import sparkle_settings
from sparkle_help.sparkle_settings import SettingState
from sparkle_help import argparse_custom as ac
from sparkle_help.sparkle_command_help import CommandName


def parser_function():
    """Define the command line arguments."""
    sgh.settings = sparkle_settings.Settings()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="re-run feature extractor for instances with previously computed features",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="run the feature extractor on multiple instances in parallel",
    )
    parser.add_argument(
        "--settings-file",
        type=Path,
        default=sgh.settings.DEFAULT_settings_path,
        action=ac.SetByUser,
        help=("specify the settings file to use in case you want to use one other than "
              "the default"),
    )
    return parser


def compute_features_parallel(my_flag_recompute):
    """Compute features in parallel."""
    if my_flag_recompute:
        feature_data_csv = sfdcsv.SparkleFeatureDataCSV(sgh.feature_data_csv_path)
        feature_data_csv.clean_csv()
        compute_features_parallel_jobid = scf.computing_features_parallel(
            Path(sgh.feature_data_csv_path), True
        )
    else:
        compute_features_parallel_jobid = scf.computing_features_parallel(
            Path(sgh.feature_data_csv_path), False
        )

    dependency_jobid_list = []

    if compute_features_parallel_jobid:
        dependency_jobid_list.append(compute_features_parallel_jobid)

    # Update feature data csv after the last job is done
    job_script = "Commands/sparkle_help/sparkle_csv_merge_help.py"
    compute_features_parallel_jobid = sjph.running_job_parallel(
        job_script, dependency_jobid_list, CommandName.COMPUTE_FEATURES
    )
    dependency_jobid_list.append(compute_features_parallel_jobid)

    job_id_str = ",".join(dependency_jobid_list)
    print(f"Computing features in parallel. Waiting for Slurm job(s) with id(s): "
          f"{job_id_str}")

    return


if __name__ == "__main__":
    # Initialise settings
    global settings
    sgh.settings = sparkle_settings.Settings()

    # Log command call
    sl.log_command(sys.argv)

    # Define command line arguments
    parser = parser_function()

    # Process command line arguments
    args = parser.parse_args()
    my_flag_recompute = args.recompute
    my_flag_parallel = args.parallel

    if ac.set_by_user(args, "settings_file"):
        sgh.settings.read_settings_ini(
            args.settings_file, SettingState.CMD_LINE
        )  # Do first, so other command line options can override settings from the file

    # Start compute features
    print("Start computing features ...")

    if not my_flag_parallel:
        if my_flag_recompute:
            feature_data_csv = sfdcsv.SparkleFeatureDataCSV(
                sgh.feature_data_csv_path
            )
            feature_data_csv.clean_csv()
            scf.computing_features(Path(sgh.feature_data_csv_path), True)
        else:
            scf.computing_features(Path(sgh.feature_data_csv_path), False)

        print("Feature data file " + sgh.feature_data_csv_path + " has been updated!")
        print("Computing features done!")
    else:
        compute_features_parallel(my_flag_recompute)

    # Write used settings to file
    sgh.settings.write_used_settings()
