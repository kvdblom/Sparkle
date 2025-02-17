#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper functions for algorithm configuration."""
import os
import sys
from pathlib import Path
from enum import Enum

import global_variables as sgh
import sparkle_logging as sl
from sparkle.types.objective import PerformanceMeasure


class InstanceType(Enum):
    """Enum of possible instance types."""
    TRAIN = 1
    TEST = 2


def get_smac_run_obj() -> str:
    """Return the SMAC run objective.

    Returns:
        A string that represents the run objective set in the settings.
    """
    # Get smac_run_obj from general settings
    smac_run_obj = sgh.settings.get_general_sparkle_objectives()[0].PerformanceMeasure

    # Convert to SMAC format
    if smac_run_obj == PerformanceMeasure.RUNTIME:
        smac_run_obj = smac_run_obj.name
    elif smac_run_obj == PerformanceMeasure.QUALITY_ABSOLUTE_MINIMISATION:
        smac_run_obj = "QUALITY"
    elif smac_run_obj == PerformanceMeasure.QUALITY_ABSOLUTE_MAXIMISATION:
        print("Warning: Performance measure not available for SMAC: {smac_run_obj}")
    else:
        print("Warning: Unknown performance measure", smac_run_obj,
              "! This is a bug in Sparkle.")

    return smac_run_obj


def get_smac_settings() -> tuple[str]:
    """Return the SMAC settings.

    Returns:
        A tuple containing all settings important to SMAC.
    """
    smac_each_run_cutoff_length = sgh.settings.get_smac_target_cutoff_length()
    smac_run_obj = get_smac_run_obj()
    smac_whole_time_budget = sgh.settings.get_config_budget_per_run()
    smac_each_run_cutoff_time = sgh.settings.get_general_target_cutoff_time()
    num_of_smac_run = sgh.settings.get_config_number_of_runs()
    num_of_smac_run_in_parallel = sgh.settings.get_slurm_number_of_runs_in_parallel()

    return (smac_run_obj, smac_whole_time_budget, smac_each_run_cutoff_time,
            smac_each_run_cutoff_length, num_of_smac_run, num_of_smac_run_in_parallel)


def check_configuration_exists() -> bool:
    """Check if the results directory for the solver and instance set combination exists.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        True if the results directory for this configuration exists.
    """
    # Check the results directory exists
    res_path = sgh.settings.get_general_sparkle_configurator().scenario.result_directory
    all_good = res_path.is_dir()

    if not all_good:
        print("ERROR: No configuration results found for the given solver and training "
              "instance set.")
        sys.exit(-1)

    return all_good


def check_instance_list_file_exist() -> None:
    """Check the instance list file exists.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    file_name = sgh.settings.get_general_sparkle_configurator()\
        .scenario.instance_file_path
    all_good = file_name.is_file()

    if not all_good:
        print("ERROR: Instance list file not found, make sure configuration was "
              "completed correctly for this solver and instance set combination.\n"
              f"Missing file:\n{file_name}\n")
        sys.exit(-1)


def check_configuration_permission_error() -> None:
    """Check the files for solver permission errors.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    res_dir = sgh.settings.get_general_sparkle_configurator().scenario.result_directory

    # Get the name of the first file in the directory
    # If there is an error, it will be in all files, so checking one is sufficient
    filename = next((res_dir / f) for f in os.listdir(res_dir)
                    if (res_dir / f).is_file())

    with Path(filename).open("r") as file:
        content = file.read()
        if "exec failed: Permission denied" in content:
            print("ERROR: The solver configuration was not succesfull so the validation "
                  "could not be completed. This is due to missing execution permissions "
                  "for the solver executable.")
            sys.exit(-1)


def check_validation_prerequisites() -> None:
    """Validate prerequisites for validation are available.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    check_configuration_exists()
    check_instance_list_file_exist()
    check_configuration_permission_error()


def write_configuration_str(configuration_str: str) -> None:
    """Write the latest optimised configuration parameter string to file.

    Args:
        configuration_str: Optimised configuration parameter string
    """
    latest_configuration_str_path = sgh.sparkle_tmp_path + "latest_configuration.txt"

    with Path(latest_configuration_str_path).open("w") as outfile:
        outfile.write(configuration_str)

    sl.add_output(latest_configuration_str_path, "Configured algorithm parameters of the"
                  " most recent configuration process")


def check_optimised_configuration_params(params: str) -> None:
    """Check if a given configuration parameter string appears to be valid.

    Args:
        params: Parameters to be checked
    """
    if params == "":
        print(f"ERROR: Invalid optimised_configuration_str: {params}; "
              "Stopping execution!")
        sys.exit(-1)


def check_optimised_configuration_performance(performance: str) -> None:
    """Check if a given configuration performance string appears to be valid.

    Args:
        performance: Performance value to be checked
    """
    if performance == -1:
        print("ERROR: Invalid optimised_configuration_performance; Stopping execution!")
        sys.exit(-1)


def check_optimised_configuration_seed(seed: str) -> None:
    """Check if a given configuration seed string appears to be valid.

    Args:
        seed: Seed value to be checked
    """
    if seed == -1:
        print("ERROR: Invalid optimised_configuration_seed; Stopping execution!")
        sys.exit(-1)


def get_optimised_configuration_params(solver_name: str, instance_set_name: str) -> str:
    """Return the optimised configuration parameter string.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        String containing the optimised configuration
    """
    optimised_configuration_str, _, _ = get_optimised_configuration_from_file(
        solver_name, instance_set_name)
    check_optimised_configuration_params(optimised_configuration_str)

    return optimised_configuration_str


def get_optimised_configuration_from_file(solver_name: str, instance_set_name: str
                                          ) -> tuple[str, str, str]:
    """Read the optimised configuration, its performance, and seed from SMAC file.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        A tuple containing string, performance, and seed of optimised configuration
    """
    optimised_configuration_str = ""
    optimised_configuration_performance = -1
    optimised_configuration_seed = -1
    configurator = sgh.settings.get_general_sparkle_configurator()
    if configurator.scenario is None:
        configurator.set_scenario_dirs(solver_name, instance_set_name)
    scen_results_dir = configurator.scenario.result_directory
    target_alg = configurator.configurator_target.name
    line_key_prefix = "Estimated mean quality of final incumbent config"
    # Compare results of each run on the training set to find the best configuration
    # among them
    for result_file in scen_results_dir.iterdir():
        smac_output_line = ""
        target_call = ""
        extra_info_statement = ""
        lines = result_file.open("r+").readlines()
        for index, line in enumerate(lines):
            if line.startswith(line_key_prefix):
                smac_output_line = line.strip().split()
                # The call is printed two lines below the output
                target_call = lines[index + 2].strip()
                # Format the target_call to only contain the actuall call
                target_call =\
                    target_call[target_call.find(target_alg):]
                extra_info_statement = lines[index + 3].strip()
        # TODO: General implementation of configurator output verification
        # Check whether the smac_output is empty
        if len(smac_output_line) == 0:
            print(f"Error: Configurator output file {result_file} has unexpected format")
            # Find matching error file
            error_files = [file for file in configurator.tmp_path.iterdir()
                           if file.name.startswith(f"{solver_name}_{instance_set_name}")
                           and file.suffix == ".err"]
            # Output content of error file
            if error_files and error_files[0].exists():
                error_file = error_files[0]
                with error_file.open("r") as file:
                    file_content = file.read()
                    print(f"Error log {error_file}:")
                    print(file_content)
                sys.exit(-1)
        # The 15th item contains the performance as float, but has trailing char
        this_configuration_performance = float(smac_output_line[14][:-1])
        # We look for the data with the highest performance
        if (optimised_configuration_performance < 0
                or this_configuration_performance < optimised_configuration_performance):
            optimised_configuration_performance = this_configuration_performance
            # Extract the configured parameters
            first_idx_config_param = target_call.find(" -")
            optimised_configuration_str = target_call[first_idx_config_param:]
            # Extract the seed
            optimised_configuration_seed = extra_info_statement.split()[4]

    return (optimised_configuration_str, optimised_configuration_performance,
            optimised_configuration_seed)


def get_optimised_configuration(solver_name: str,
                                instance_set_name: str) -> tuple[str, str, str]:
    """Return the optimised configuration str, its performance, and its seed.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        A tuple containing string, performance, and seed of optimised configuration
    """
    (optimised_configuration_str, optimised_configuration_performance,
     optimised_configuration_seed) = get_optimised_configuration_from_file(
        solver_name, instance_set_name)
    check_optimised_configuration_params(optimised_configuration_str)
    check_optimised_configuration_performance(optimised_configuration_performance)
    check_optimised_configuration_seed(optimised_configuration_seed)
    return (optimised_configuration_str, optimised_configuration_performance,
            optimised_configuration_seed)
