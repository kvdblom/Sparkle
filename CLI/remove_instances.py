#!/usr/bin/env python3
"""Sparkle command to remove an instance set from the Sparkle platform."""

import sys
import argparse
import shutil
from pathlib import Path

import global_variables as gv
from sparkle.platform import file_help as sfh
from sparkle.structures import feature_data_csv_help as sfdcsv
from sparkle.structures.performance_dataframe import PerformanceDataFrame
import sparkle_logging as sl
from sparkle.instance import instances_help as sih
from CLI.help import command_help as ch
from CLI.initialise import check_for_initialise


def parser_function() -> argparse.ArgumentParser:
    """Define the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "instances_path",
        metavar="instances-path",
        type=str,
        help="path to or nickname of the instance set",
    )
    parser.add_argument(
        "--nickname",
        action="store_true",
        help="if given instances_path is used as a nickname for the instance set",
    )

    return parser


if __name__ == "__main__":
    # Log command call
    sl.log_command(sys.argv)

    # Define command line arguments
    parser = parser_function()

    # Process command line arguments
    args = parser.parse_args()
    instances_path = Path(args.instances_path)

    check_for_initialise(sys.argv,
                         ch.COMMAND_DEPENDENCIES[ch.CommandName.REMOVE_INSTANCES])

    if args.nickname or not instances_path.exists():
        # Try to resolve the argument as a nickname
        instances_path = gv.instance_dir / instances_path
    if not instances_path.exists():
        print(f'Could not resolve instances path arg "{args.instances_path}"!')
        print("Check that the path or nickname is spelled correctly.")
        sys.exit(-1)

    print(f"Start removing all instances in directory {instances_path} ...")
    list_all_filename = sfh.get_list_all_filename_recursive(instances_path)

    feature_data_csv = sfdcsv.SparkleFeatureDataCSV(gv.feature_data_csv_path)
    performance_data_csv = PerformanceDataFrame(gv.performance_data_csv_path)

    for intended_instance in list_all_filename:
        intended_instance_name = intended_instance.name
        # Remove instance records
        sfh.add_remove_platform_item(intended_instance_name,
                                     gv.instance_list_path, remove=True)
        feature_data_csv.delete_row(intended_instance_name)
        performance_data_csv.remove_instance(intended_instance_name)

        print(f"Instance {intended_instance} has been removed from platform!")

    if instances_path.exists() and instances_path.is_dir():
        shutil.rmtree(instances_path)
        print(f"Instance set {instances_path} has been removed!")
    else:
        print(f"Warning: Path {instances_path} did not exist. Continuing")

    # Remove instance reference list (for multi-file instances)
    sih.remove_reference_instance_list(instances_path.name)

    feature_data_csv.save_csv()
    performance_data_csv.save_csv()

    if Path(gv.sparkle_algorithm_selector_path).exists():
        shutil.rmtree(gv.sparkle_algorithm_selector_path)
        print("Removing Sparkle portfolio selector "
              f"{gv.sparkle_algorithm_selector_path} done!")

    if Path(gv.sparkle_report_path).exists():
        shutil.rmtree(gv.sparkle_report_path)
        print(f"Removing Sparkle report {gv.sparkle_report_path} done!")

    print(f"Removing instances in directory {instances_path} done!")
