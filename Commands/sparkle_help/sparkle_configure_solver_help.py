#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper functions for algorithm configuration."""

import os
import sys
import fcntl
from pathlib import Path
from pathlib import PurePath
from enum import Enum

from Commands.sparkle_help import sparkle_file_help as sfh
from Commands.sparkle_help import sparkle_global_help as sgh
from Commands.sparkle_help import sparkle_logging as sl
from Commands.sparkle_help.sparkle_settings import PerformanceMeasure
from Commands.sparkle_help import sparkle_instances_help as sih


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
    smac_run_obj = sgh.settings.get_general_performance_measure()

    # Convert to SMAC format
    if smac_run_obj == PerformanceMeasure.RUNTIME:
        smac_run_obj = smac_run_obj.name
    elif smac_run_obj == PerformanceMeasure.QUALITY_ABSOLUTE:
        smac_run_obj = "QUALITY"
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


def copy_file_instance(solver_name: str, instance_set_train_name: str,
                       instance_set_target_name: str, instance_type: str) -> None:
    """Copy instance file to the solver directory with the specified postfix.

    Args:
        solver_name: Name of the solver
        instance_set_train_name: Name of the instance set for training
        instance_set_target_name: Target name of the instance set
        instance_type: Instance type used for the file postfix
    """
    file_postfix = f"_{instance_type}.txt"

    smac_solver_dir = get_smac_solver_dir(solver_name, instance_set_train_name)
    smac_file_instance_path_ori = (f"{sgh.smac_dir}scenarios/instances/"
                                   f"{instance_set_target_name}{file_postfix}")
    smac_file_instance_path_target = (
        smac_solver_dir + instance_set_target_name + file_postfix)

    command_line = f"cp {smac_file_instance_path_ori} {smac_file_instance_path_target}"
    os.system(command_line)

    log_str = "List of instances to be used for configuration"
    sl.add_output(smac_file_instance_path_target, log_str)


def get_solver_deterministic(solver_name: str) -> str:
    """Return a string indicating whether a given solver is deterministic or not.

    Args:
        solver_name: Name of the solver to check

    Returns:
        A string containing 0 or 1 indicating whether solver is deterministic
    """
    deterministic = ""
    target_solver_path = "Solvers/" + solver_name
    solver_list_path = sgh.solver_list_path

    fin = Path(solver_list_path).open("r+")
    fcntl.flock(fin.fileno(), fcntl.LOCK_EX)

    while True:
        myline = fin.readline()
        if not myline:
            break
        myline = myline.strip()
        mylist = myline.split()

        if (mylist[0] == target_solver_path):
            deterministic = mylist[1]
            break

    return deterministic


def create_file_scenario_validate(solver_name: str, instance_set_train_name: str,
                                  instance_set_val_name: str,
                                  instance_type: InstanceType, default: bool) -> str:
    """Create a file with the configuration scenario to be used for SMAC validation.

    This will be located in the solver directory.

    Args:
        solver_name: Name of the solver
        instance_set_train_name: Name of training instance set
        instance_set_val_name: Name of the validation instance set
        instance_type: Instance type (train or test)
        default: Whether the configured or default settings should be used

    Returns:
        String containing the name of the scenario file
    """
    if instance_type is InstanceType.TRAIN:
        inst_type = "train"
    else:
        inst_type = "test"

    if default is True:
        config_type = "default"
    else:
        config_type = "configured"

    smac_solver_dir = get_smac_solver_dir(solver_name, instance_set_train_name)
    scenario_file_name = (
        f"{instance_set_val_name}_{inst_type}_{config_type}_scenario.txt")
    smac_file_scenario = smac_solver_dir + scenario_file_name

    (smac_run_obj, smac_whole_time_budget, smac_each_run_cutoff_time,
     smac_each_run_cutoff_length, _, _) = get_smac_settings()

    smac_paramfile = (f"scenarios/{solver_name}_{instance_set_train_name}/"
                      f"{get_pcs_file_from_solver_directory(Path(smac_solver_dir))}")
    if instance_type == InstanceType.TRAIN:
        smac_outdir = (f"scenarios/{solver_name}_{instance_set_train_name}/"
                       f"outdir_{inst_type}_{config_type}/")
    else:
        smac_outdir = (f"scenarios/{solver_name}_{instance_set_train_name}/"
                       f"outdir_{instance_set_val_name}_{inst_type}_{config_type}/")
    smac_instance_file = (f"scenarios/instances/{instance_set_train_name}/"
                          f"{instance_set_val_name}_{inst_type}.txt")
    smac_test_instance_file = smac_instance_file

    fout = Path(smac_file_scenario).open("w+")
    fout.write("algo = ./" + sgh.sparkle_smac_wrapper + "\n")
    fout.write(f"execdir = scenarios/{solver_name}_{instance_set_train_name}/\n")
    fout.write("deterministic = " + get_solver_deterministic(solver_name) + "\n")
    fout.write("run_obj = " + smac_run_obj + "\n")
    fout.write("wallclock-limit = " + str(smac_whole_time_budget) + "\n")
    fout.write("cutoffTime = " + str(smac_each_run_cutoff_time) + "\n")
    fout.write("cutoff_length = " + smac_each_run_cutoff_length + "\n")
    fout.write("paramfile = " + smac_paramfile + "\n")
    fout.write("outdir = " + smac_outdir + "\n")
    fout.write("instance_file = " + smac_instance_file + "\n")
    fout.write("test_instance_file = " + smac_test_instance_file + "\n")
    fout.close()

    log_str = (f"SMAC Scenario file for the validation of the {config_type} solver "
               f"{solver_name} on the {inst_type}ing set")
    sl.add_output(smac_file_scenario, log_str)

    return scenario_file_name


def get_smac_solver_dir(solver_name: str, instance_set_name: str) -> str:
    """Return the directory of a solver under the SMAC directory.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        String containing the scenario directory inside SMAC
    """
    smac_scenario_dir = f"{sgh.smac_dir}/scenarios"
    smac_solver_dir = f"{smac_scenario_dir}/{solver_name}_{instance_set_name}/"

    return smac_solver_dir


def get_pcs_file_from_solver_directory(solver_directory: Path) -> Path:
    """Return the name of the PCS file in a solver directory.

    If not found, return an empty str.

    Args:
        solver_directory: Directory of solver

    Returns:
        Returns string containing the name of pcs file if found
    """
    for file_path in Path(solver_directory).iterdir():
        file_extension = "".join(file_path.suffixes)

        if file_extension == ".pcs":
            return file_path.name

    return ""


def remove_validation_directories_execution_or_output(solver_name: str,
                                                      instance_set_train_name: str,
                                                      instance_set_test_name: str,
                                                      exec_or_out: str) -> None:
    """Remove execution or output directories for validation.

    Args:
        solver_name: Name of the solver
        instance_set_train_name: Name of instance set for training
        instance_set_test_name: Name of instance set for testing
        exec_or_out: Postfix describing if execution or output directory is used
    """
    solver_dir = get_smac_solver_dir(solver_name, instance_set_train_name) + exec_or_out

    train_default_dir = Path(solver_dir + "_train_default/")
    sfh.rmtree(train_default_dir)

    if instance_set_test_name is not None:
        test_default_dir = Path(
            solver_dir + "_" + instance_set_test_name + "_test_default/")
        sfh.rmtree(test_default_dir)

        test_configured_dir = Path(
            solver_dir + "_" + instance_set_test_name + "_test_configured/")
        sfh.rmtree(test_configured_dir)


def remove_validation_directories(solver_name: str, instance_set_train_name: str,
                                  instance_set_test_name: str) -> None:
    """Remove validation directories for a solver and instance set(s) combination.

    Args:
        solver_name: Name of the solver
        instance_set_train_name: Name of the instance set for training
        instance_set_test_name: Name of the instance set for testing
    """
    remove_validation_directories_execution_or_output(
        solver_name, instance_set_train_name, instance_set_test_name, "validate")
    remove_validation_directories_execution_or_output(
        solver_name, instance_set_train_name, instance_set_test_name, "output")


def prepare_smac_execution_directories_validation(solver_name: str,
                                                  instance_set_train_name: str,
                                                  instance_set_test_name: str) -> None:
    """Create and copy required directories and files for validation with SMAC.

    Remove old directories and files as needed.

    Args:
        solver_name: Name of the solver
        instance_set_train_name: Name of the instance set for training
        instance_set_test_name: Name of the instance set for testing
    """
    # Make sure no old files remain that could interfere
    remove_validation_directories(solver_name, instance_set_train_name,
                                  instance_set_test_name)

    smac_solver_dir = get_smac_solver_dir(solver_name, instance_set_train_name)
    _, _, _, _, num_of_smac_run, _ = get_smac_settings()

    for i in range(1, num_of_smac_run + 1):
        solver_directory = f"Solvers/{solver_name}/*"

        # Train default
        execdir = "validate_train_default/"

        # Create directories, -p makes sure any missing parents are also created
        cmd = f"mkdir -p {smac_solver_dir}{execdir}"
        os.system(cmd)
        # Copy solver to execution directory
        cmd = f"cp -r {solver_directory} {smac_solver_dir}{execdir}"
        os.system(cmd)

        # Test default
        if instance_set_test_name is not None:
            execdir = f"validate_{instance_set_test_name}_test_default/"

            # Create directories, -p makes sure any missing parents are also created
            cmd = f"mkdir -p {smac_solver_dir}{execdir}"
            os.system(cmd)
            # Copy solver to execution directory
            cmd = f"cp -r {solver_directory} {smac_solver_dir}{execdir}"
            os.system(cmd)

            # Test configured
            execdir = f"validate_{instance_set_test_name}_test_configured/"

            # Create directories, -p makes sure any missing parents are also created
            cmd = f"mkdir -p {smac_solver_dir}{execdir}"
            os.system(cmd)
            # Copy solver to execution directory
            cmd = f"cp -r {solver_directory} {smac_solver_dir}{execdir}"
            os.system(cmd)


def check_configuration_exists(solver_name: str, instance_set_name: str) -> None:
    """Check if the results directory for the solver and instance set combination exists.

    NOTE: This function assumes SMAC output

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        True if the results directory for this configuration exists.
    """
    # Check the results directory exists
    smac_results_dir = Path(f"{sgh.smac_dir}/results/{solver_name}_{instance_set_name}/")
    all_good = smac_results_dir.is_dir()

    if not all_good:
        print("ERROR: No configuration results found for the given solver and training "
              "instance set.")
        sys.exit(-1)

    return all_good


def check_instance_list_file_exist(solver_name: str, instance_set_name: str) -> None:
    """Check the instance list file exists.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    file_name = Path(instance_set_name + "_train.txt")
    instance_list_file_path = Path(PurePath(Path(sgh.smac_dir)
                                   / Path("scenarios")
                                   / Path("instances")
                                   / Path(instance_set_name)
                                   / file_name))

    all_good = instance_list_file_path.is_file()

    if not all_good:
        print("ERROR: Instance list file not found, make sure configuration was "
              "completed correctly for this solver and instance set combination.")
        sys.exit(-1)


def check_configuration_permission_error(solver_name: str,
                                         instance_set_name: str) -> None:
    """Check the files for solver permission errors.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    smac_results_dir = Path(f"{sgh.smac_dir}/results/{solver_name}_{instance_set_name}/")

    # Get the name of the first file in the directory
    # If there is an error, it will be in all files, so checking one is sufficient
    filename = next(Path(smac_results_dir / f) for f in os.listdir(smac_results_dir)
                    if Path(smac_results_dir / f).is_file())

    with Path(filename).open("r") as file:
        content = file.read()
        if "exec failed: Permission denied" in content:
            print("ERROR: The solver configuration was not succesfull so the validation "
                  "could not be completed. This is due to missing execution permissions "
                  "for the solver executable.")
            sys.exit(-1)


def check_validation_prerequisites(solver_name: str, instance_set_name: str) -> None:
    """Validate prerequisites for validation are available.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    check_configuration_exists(solver_name, instance_set_name)
    check_instance_list_file_exist(solver_name, instance_set_name)
    check_configuration_permission_error(solver_name, instance_set_name)


def write_optimised_configuration_str(solver_name: str, instance_set_name: str) -> None:
    """Write the latest optimised configuration parameter string to file.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    optimised_configuration_str, _, _ = get_optimised_configuration(
        solver_name, instance_set_name)
    latest_configuration_str_path = sgh.sparkle_tmp_path + "latest_configuration.txt"

    with Path(latest_configuration_str_path).open("w") as outfile:
        outfile.write(optimised_configuration_str)

    sl.add_output(latest_configuration_str_path, "Configured algorithm parameters of the"
                  " most recent configuration process")


def write_optimised_configuration_pcs(solver_name: str, instance_set_name: str) -> None:
    """Write optimised configuration to a new PCS file.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set
    """
    # Read optimised configuration and convert to dict
    optimised_configuration_str, _, _ = get_optimised_configuration(
        solver_name, instance_set_name)
    optimised_configuration_str += " -arena '12345'"
    optimised_configuration_list = optimised_configuration_str.split()

    # Create dictionary
    config_dict = {}
    for i in range(0, len(optimised_configuration_list), 2):
        # Remove dashes and spaces from parameter names, and remove quotes and
        # spaces from parameter values before adding them to the dict
        config_dict[optimised_configuration_list[i].strip(" -")] = (
            optimised_configuration_list[i + 1].strip(" '"))

    # Read existing PCS file and create output content
    solver_directory = Path("Solvers", solver_name)
    pcs_file = solver_directory / get_pcs_file_from_solver_directory(
        solver_directory)
    pcs_file_out = []

    with Path(pcs_file).open() as infile:
        for line in infile:
            # Copy empty lines
            if not line.strip():
                line_out = line
            # Don't mess with conditional (containing '|') and forbidden (starting
            # with '{') parameter clauses, copy them as is
            elif "|" in line or line.startswith("{"):
                line_out = line
            # Also copy parameters that do not appear in the optimised list
            # (if the first word in the line does not match one of the parameter names
            # in the dict)
            elif line.split()[0] not in config_dict:
                line_out = line
            # Modify default values with optimised values
            else:
                words = line.split("[")
                if len(words) == 2:
                    # Second element is default value + possible tail
                    param_name = line.split()[0]
                    param_val = config_dict[param_name]
                    tail = words[1].split("]")[1]
                    line_out = words[0] + "[" + param_val + "]" + tail
                elif len(words) == 3:
                    # Third element is default value + possible tail
                    param_name = line.split()[0]
                    param_val = config_dict[param_name]
                    tail = words[2].split("]")[1]
                    line_out = words[0] + words[1] + "[" + param_val + "]" + tail
                else:
                    # This does not seem to be a line with a parameter definition, copy
                    # as is
                    line_out = line
            pcs_file_out.append(line_out)

    latest_configuration_pcs_path = sgh.sparkle_tmp_path + "latest_configuration.pcs"

    with Path(latest_configuration_pcs_path).open("w") as outfile:
        for element in pcs_file_out:
            outfile.write(str(element))
    # Log output
    sl.add_output(latest_configuration_pcs_path, "PCS file with configured algorithm "
                  "parameters of the most recent configuration process as default "
                  "values")


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
    """Read the optimised configuration, its performance, and seed from file.

    Args:
        solver_name: Name of the solver
        instance_set_name: Name of the instance set

    Returns:
        A tuple containing string, performance, and seed of optimised configuration
    """
    optimised_configuration_str = ""
    optimised_configuration_performance = -1
    optimised_configuration_seed = -1

    smac_results_dir = f"{sgh.smac_dir}results/{solver_name}_{instance_set_name}/"
    list_file_result_name = os.listdir(smac_results_dir)
    key_str_1 = "Estimated mean quality of final incumbent config"

    # Compare results of each run on the training set to find the best configuration
    # among them
    for file_result_name in list_file_result_name:
        file_result_path = smac_results_dir + file_result_name
        fin = Path(file_result_path).open("r+")

        while True:
            myline = fin.readline()
            if not myline:
                break
            myline = myline.strip()

            if myline.find(key_str_1) == 0:
                mylist = myline.split()
                # Skip 14 words leading up to the performance value
                this_configuration_performance = float(mylist[14][:-1])

                if (optimised_configuration_performance < 0
                   or this_configuration_performance
                   < optimised_configuration_performance):
                    optimised_configuration_performance = this_configuration_performance

                    # Skip the line before the line with the optimised configuration
                    myline_2 = fin.readline()
                    myline_2 = fin.readline()
                    # If this is a single file instance:
                    if not sih.check_existence_of_reference_instance_list(
                            instance_set_name):
                        mylist_2 = myline_2.strip().split()
                        # Skip 8 words before the configured parameters
                        start_index = 8
                    # Otherwise, for multi-file instances:
                    else:
                        # Skip everything before the last double quote "
                        mylist_2 = myline_2.strip().split('"')
                        last_idx = len(mylist_2) - 1
                        mylist_2 = mylist_2[last_idx].strip().split()
                        # Then skip another 4 words before the configured parameters
                        start_index = 4
                    end_index = len(mylist_2)
                    optimised_configuration_str = ""
                    for i in range(start_index, end_index):
                        optimised_configuration_str += " " + mylist_2[i]

                    # Get seed used to call smac
                    myline_3 = fin.readline()
                    mylist_3 = myline_3.strip().split()
                    optimised_configuration_seed = mylist_3[4]

        fin.close()

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
