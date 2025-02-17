#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper functions for portfolio selector construction."""
import subprocess
import sys
import shutil
from pathlib import Path, PurePath

import global_variables as sgh
from sparkle.platform import file_help as sfh
from sparkle.structures import feature_data_csv_help as sfdcsv
from sparkle.structures.performance_dataframe import PerformanceDataFrame
from CLI.support import run_solvers_help as srsh
from sparkle.instance import compute_features_help as scfh
import sparkle_logging as sl
from sparkle.types.objective import PerformanceMeasure


def data_unchanged(sparkle_portfolio_selector_path: Path) -> bool:
    """Return whether data has changed since the last portfolio selector construction.

    Args:
        sparkle_portfolio_selector_path: Portfolio selector path.

    Returns:
        True if neither performance data id and feature data id remain the same.
    """
    pd_id = srsh.get_performance_data_id()
    fd_id = scfh.get_feature_data_id()
    selector_dir = sparkle_portfolio_selector_path.parent
    selector_pd_id = get_selector_pd_id(selector_dir)
    selector_fd_id = get_selector_fd_id(selector_dir)

    return pd_id == selector_pd_id and fd_id == selector_fd_id


def write_selector_pd_id(sparkle_portfolio_selector_path: Path) -> None:
    """Write the ID of the performance data used to construct the portfolio selector.

    Args:
        sparkle_portfolio_selector_path: Portfolio selector path.
    """
    # Get pd_id
    pd_id = srsh.get_performance_data_id()

    # Write pd_id
    pd_id_path = Path(sparkle_portfolio_selector_path.parent / "pd.id")

    with pd_id_path.open("w") as pd_id_file:
        pd_id_file.write(str(pd_id))

        # Add file to log
        sl.add_output(str(pd_id_path), "ID of the performance data used to construct "
                      "the portfolio selector.")


def get_selector_pd_id(selector_dir: PurePath) -> int:
    """Return the ID of the performance data used to construct the portfolio selector.

    Args:
        selector_dir: Selector directory path.

    Returns:
        Selector performance data ID, -1 if no file with a saved ID is found.
    """
    pd_id_path = Path(selector_dir / "pd.id")

    try:
        with pd_id_path.open("r") as pd_id_file:
            pd_id = int(pd_id_file.readline())
    except FileNotFoundError:
        pd_id = -1

    return pd_id


def write_selector_fd_id(sparkle_portfolio_selector_path: Path) -> None:
    """Write the ID of the feature data used to construct the portfolio selector.

    Args:
        sparkle_portfolio_selector_path: Portfolio selector path.
    """
    # Get fd_id
    fd_id = scfh.get_feature_data_id()

    # Write fd_id
    fd_id_path = Path(sparkle_portfolio_selector_path.parent / "fd.id")

    with fd_id_path.open("w") as fd_id_file:
        fd_id_file.write(str(fd_id))

        # Add file to log
        sl.add_output(str(fd_id_path),
                      "ID of the feature data used to construct the portfolio selector.")


def get_selector_fd_id(selector_dir: PurePath) -> int:
    """Return the ID of the feature data used to construct the portfolio selector.

    Args:
        selector_dir: Selector directory path.

    Returns:
        Selector feature data ID, -1 if no file with a saved ID is found.
    """
    fd_id_path = Path(selector_dir / "fd.id")

    try:
        with fd_id_path.open("r") as fd_id_file:
            fd_id = int(fd_id_file.readline())
    except FileNotFoundError:
        fd_id = -1

    return fd_id


def construct_sparkle_portfolio_selector(selector_path: Path,
                                         performance_data_csv_path: str,
                                         feature_data_csv_path: str,
                                         flag_recompute: bool = False) -> bool:
    """Create the Sparkle portfolio selector.

    Args:
        selector_path: Portfolio selector path.
        performance_data_csv_path: Performance data csv path.
        feature_data_csv_path: Feature data csv path.
        flag_recompute: Whether or not to recompute if the selector exists and no data
            was changed. Defaults to False.

    Returns:
        True if portfolio construction is successful.
    """
    # If the selector exists and the data didn't change, do nothing;
    # unless the recompute flag is set
    if selector_path.exists() and data_unchanged(selector_path) and not flag_recompute:
        print("Portfolio selector already exists for the current feature and performance"
              " data.")

        # Nothing to do, success!
        return True

    # Remove contents of- and the selector path to ensure everything is (re)computed
    # for the new selector when required
    shutil.rmtree(selector_path.parent, ignore_errors=True)

    # (Re)create the path to the selector
    selector_path.parent.mkdir(parents=True, exist_ok=True)

    cutoff_time = sgh.settings.get_general_target_cutoff_time()
    cutoff_time_minimum = 2

    # AutoFolio cannot handle cutoff time less than 2, adjust if needed
    if cutoff_time < cutoff_time_minimum:
        print(f"Warning: A cutoff time of {cutoff_time} is too small for AutoFolio, "
              f"setting it to {cutoff_time_minimum}")
        cutoff_time = cutoff_time_minimum

    cutoff_time_str = str(cutoff_time)
    python_executable = sgh.python_executable
    perf_measure = sgh.settings.get_general_sparkle_objectives()[0].PerformanceMeasure
    if perf_measure == PerformanceMeasure.RUNTIME:
        objective_function = "--objective runtime"
    elif perf_measure == PerformanceMeasure.QUALITY_ABSOLUTE_MAXIMISATION or\
            perf_measure == PerformanceMeasure.QUALITY_ABSOLUTE_MINIMISATION:
        objective_function = "--objective solution_quality"
    else:
        print("ERROR: Unknown performance measure in "
              "construct_sparkle_portfolio_selector")
        sys.exit(-1)

    if not Path(r"Tmp/").exists():
        Path(r"Tmp/").mkdir()

    feature_data_csv = sfdcsv.SparkleFeatureDataCSV(feature_data_csv_path)
    bool_exists_missing_value = feature_data_csv.bool_exists_missing_value()

    if bool_exists_missing_value:
        print("****** WARNING: There are missing values in the feature data, and all "
              "missing values will be imputed as the mean value of all other non-missing"
              " values! ******")
        print("Imputing all missing values starts ...")
        feature_data_csv.impute_missing_value_of_all_columns()
        print("Imputing all missing values done!")
        impute_feature_data_csv_path = (
            f"{feature_data_csv_path}_{sgh.get_time_pid_random_string()}"
            "_impute.csv")
        feature_data_csv.save_csv(impute_feature_data_csv_path)
        feature_data_csv_path = impute_feature_data_csv_path

    log_file = selector_path.parent.name + "_autofolio.out"
    err_file = selector_path.parent.name + "_autofolio.err"
    log_path_str = str(Path(sl.caller_log_dir / log_file))
    err_path_str = str(Path(sl.caller_log_dir / err_file))
    performance_data = PerformanceDataFrame(performance_data_csv_path)
    pf_data_autofolio_path = performance_data.to_autofolio()
    cmd_list = [python_executable, sgh.autofolio_path, "--performance_csv",
                str(pf_data_autofolio_path), "--feature_csv", feature_data_csv_path,
                objective_function, "--runtime_cutoff", cutoff_time_str, "--tune",
                "--save", str(selector_path)]
    # Write command line to log
    print("Running command below:\n", " ".join(cmd_list), file=open(log_path_str, "a+"))
    sl.add_output(log_path_str, "Command line used to construct portfolio through "
                  "AutoFolio and associated output")
    sl.add_output(err_path_str,
                  "Error output from constructing portfolio through AutoFolio")

    process = subprocess.run(cmd_list,
                             stdout=Path(log_path_str).open("w+"),
                             stderr=Path(err_path_str).open("w+"))
    sfh.rmfiles("runhistory.json")

    if bool_exists_missing_value:
        sfh.rmfiles(impute_feature_data_csv_path)

    # Check if the selector was constructed successfully
    if process.returncode != 0 or not selector_path.is_file():
        print("Sparkle portfolio selector is not successfully constructed!")
        print("There might be some errors!")
        print("Standard output log:", log_path_str)
        print("Error output log:", err_path_str)
        sys.exit(-1)

    # Remove the data copy for AutoFolio
    pf_data_autofolio_path.unlink()
    # Update data IDs associated with this selector
    write_selector_pd_id(selector_path)
    write_selector_fd_id(selector_path)

    # If we reach this point portfolio construction should be successful
    return True
