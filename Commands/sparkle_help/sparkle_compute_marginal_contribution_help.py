#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper functions for marginal contribution computation."""

from __future__ import annotations

import os
import sys
import csv
from pathlib import Path

from Commands.sparkle_help import sparkle_basic_help
from Commands.sparkle_help import sparkle_file_help as sfh
from Commands.sparkle_help import sparkle_global_help as sgh
from Commands.sparkle_help import sparkle_feature_data_csv_help as sfdcsv
from Commands.sparkle_help import sparkle_performance_data_csv_help as spdcsv
from Commands.sparkle_help.sparkle_performance_data_csv_help import \
    SparklePerformanceDataCSV
from Commands.sparkle_help import sparkle_construct_portfolio_selector_help as scps
from Commands.sparkle_help import sparkle_run_portfolio_selector_help as srps
from Commands.sparkle_help import sparkle_logging as sl
from Commands.sparkle_help.sparkle_settings import PerformanceMeasure
from Commands.sparkle_help.sparkle_feature_data_csv_help import SparkleFeatureDataCSV


def read_marginal_contribution_csv(path: Path) -> list[tuple[str, float]]:
    """Read the marginal contriutions from a CSV file.

    Args:
        path: Path to the source CSV file.

    Returns:
        A list of tuples containing the marginal contributions data.
    """
    content = []

    with path.open("r") as input_file:
        reader = csv.reader(input_file)
        for row in reader:
            # 0 is the solver, 1 the marginal contribution
            content.append((row[0], row[1]))

    return content


def write_marginal_contribution_csv(path: Path,
                                    content: list[tuple[str, float]]) -> None:
    """Write the marginal contributions to a CSV file.

    Args:
        path: Target path to the CSV file.
        content: A list of 2-tuples. The first component is the string name of the
        solver and the second is the algorithms' marginal contribution.
    """
    with path.open("w") as output_file:
        writer = csv.writer(output_file)
        writer.writerows(content)

        # Add file to log
        sl.add_output(str(path),
                      "Marginal contributions to the portfolio selector per solver.")


def get_capvalue_list(
        performance_data_csv: SparklePerformanceDataCSV) -> list[float] | None:
    """Return a list of cap-values if the performance measure is QUALITY, else None.

    Args:
        performance_data_csv: The CSV data as a SparklePerformanceDataCSV object.

    Returns:
        A list of floating point numbers or None.
    """
    performance_measure = sgh.settings.get_general_performance_measure()

    # If QUALITY_ABSOLUTE is the performance measure, use the maximum performance per
    # instance as capvalue; otherwise the cutoff time is used
    if performance_measure == PerformanceMeasure.QUALITY_ABSOLUTE:
        return performance_data_csv.get_maximum_performance_per_instance()
    return None


def compute_perfect_selector_marginal_contribution(
        performance_data_csv_path: Path = sgh.performance_data_csv_path,
        flag_recompute: bool = False) -> list[tuple[str, float]]:
    """Return the marginal contributions of solvers for the VBS.

    Args:
      performance_data_csv_path: Path to the CSV file containing the performance data.
      flag_recompute: Boolean indicating whether a recomputation of the marginal
        contribution is enforced.

    Returns:
      A list of 2-tuples of the form (solver name, marginal contribution).
    """
    perfect_margi_cont_path = sgh.sparkle_marginal_contribution_perfect_path

    # If the marginal contribution already exists in file, read it and return
    if not flag_recompute and perfect_margi_cont_path.is_file():
        print("Marginal contribution for the perfect selector already computed, reading "
              "from file instead! Use --recompute to force recomputation.")
        return read_marginal_contribution_csv(perfect_margi_cont_path)

    cutoff_time_str = str(sgh.settings.get_general_target_cutoff_time())
    print(f"In this calculation, cutoff time for each run is {cutoff_time_str} seconds")

    rank_list = []
    performance_data_csv = spdcsv.SparklePerformanceDataCSV(performance_data_csv_path)
    num_instances = performance_data_csv.get_row_size()
    num_solvers = performance_data_csv.get_column_size()
    capvalue_list = get_capvalue_list(performance_data_csv)

    print("Computing virtual best performance for portfolio selector with all solvers "
          "...")
    virtual_best_performance = (
        performance_data_csv.calc_virtual_best_performance_of_portfolio(
            num_instances, num_solvers, capvalue_list))
    print("Virtual best performance for portfolio selector with all solvers is "
          f"{str(virtual_best_performance)}")
    print("Computing done!")

    for solver in performance_data_csv.list_columns():
        print("Computing virtual best performance for portfolio selector excluding "
              f"solver {sfh.get_last_level_directory_name(solver)} ...")
        tmp_performance_data_csv = spdcsv.SparklePerformanceDataCSV(
            performance_data_csv_path)
        tmp_performance_data_csv.delete_column(solver)
        tmp_virtual_best_performance = (
            tmp_performance_data_csv.calc_virtual_best_performance_of_portfolio(
                num_instances, num_solvers, capvalue_list))
        print("Virtual best performance for portfolio selector excluding solver "
              f"{sfh.get_last_level_directory_name(solver)} is "
              f"{str(tmp_virtual_best_performance)}")
        print("Computing done!")
        marginal_contribution = virtual_best_performance - tmp_virtual_best_performance
        solver_tuple = (solver, marginal_contribution)
        rank_list.append(solver_tuple)
        print("Marginal contribution (to Perfect Selector) for solver "
              f"{sfh.get_last_level_directory_name(solver)} is "
              f"{str(marginal_contribution)}")

    rank_list.sort(key=lambda marginal_contribution: marginal_contribution[1],
                   reverse=True)

    # Write perfect selector contributions to file
    write_marginal_contribution_csv(perfect_margi_cont_path, rank_list)

    return rank_list


def get_list_predict_schedule(actual_portfolio_selector_path: str,
                              feature_data_csv: SparkleFeatureDataCSV,
                              instance: int) -> list[float]:
    """Return the solvers schedule suggested by the selector as a list.

    Args:
      actual_portfolio_selector_path: Path to portfolio selector.
      feature_data_csv: SparkleFeatureDataCSV object with the feature data.
      instance: Instance ID, i.e., the number of the instance.

    Returns:
      List of floating point numbers.
    """
    list_predict_schedule = []
    python_executable = sgh.python_executable
    if not Path("Tmp/").exists():
        Path("Tmp/").mkdir()
    feature_vector_string = feature_data_csv.get_feature_vector_string(instance)

    predit_schedule_file = ("predict_schedule_"
                            f"{sparkle_basic_help.get_time_pid_random_string()}.predres")
    log_file = "predict_schedule_autofolio.out"
    err_file = "predict_schedule_autofolio.err"
    predict_schedule_result_path_str = (
        str(Path(sl.caller_log_dir / predit_schedule_file)))
    log_path = Path(sl.caller_log_dir / log_file)
    err_path_str = str(Path(sl.caller_log_dir / err_file))

    command_line = (f"{python_executable} {sgh.autofolio_path} --load "
                    f'{actual_portfolio_selector_path} --feature_vec "'
                    f'{feature_vector_string}" 1> {predict_schedule_result_path_str}'
                    f" 2> {err_path_str}")

    with log_path.open("a+") as log_file:
        print("Running command below to get predicted schedule from autofolio:\n",
              command_line, file=log_file)

    os.system(command_line)

    list_predict_schedule = (
        srps.get_list_predict_schedule_from_file(predict_schedule_result_path_str))

    # If there is error output log temporary files for analsysis, otherwise remove them
    with Path(err_path_str).open() as file_content:
        lines = file_content.read().splitlines()
    if len(lines) > 1 or lines[0] != "INFO:AutoFolio:Predict on Test":
        sl.add_output(str(log_path), "Predicted portfolio schedule command line call")
        sl.add_output(predict_schedule_result_path_str, "Predicted portfolio schedule")
        sl.add_output(err_path_str, "Predicted portfolio schedule error output")
    else:
        os.system("rm -f " + predict_schedule_result_path_str)
        os.system("rm -f " + err_path_str)
        os.system("rm -f " + str(log_path))

    return list_predict_schedule


def compute_actual_selector_performance(
        actual_portfolio_selector_path: str,
        performance_data_csv_path: str,
        feature_data_csv_path: str,
        num_instances: int,
        num_solvers: int,
        capvalue_list: list[float] | None = None) -> float:
    """Return the performance of the selector over all instances.

    Args:
      actual_portfolio_selector_path: Path to portfolio selector.
      performance_data_csv_path: Path to the CSV file with the performance data.
      feature_data_csv_path: path to the CSV file with the features.
      num_instances: The number of instances.
      num_solvers: The number of solvers in the portfolio.
      capvalue_list: Optional list of cap-values.

    Returns:
      The selector performance as a single floating point number.
    """
    cutoff_time = sgh.settings.get_general_target_cutoff_time()
    performance_data_csv = spdcsv.SparklePerformanceDataCSV(performance_data_csv_path)

    actual_selector_performance = 0

    for instance_idx in range(0, len(performance_data_csv.list_rows())):
        instance = performance_data_csv.get_row_name(instance_idx)

        if capvalue_list is None:
            # RUNTIME
            capvalue = cutoff_time
            performance_this_instance, flag_successfully_solving = (
                compute_actual_used_time_for_instance(
                    actual_portfolio_selector_path, instance, feature_data_csv_path,
                    performance_data_csv))

            if flag_successfully_solving:
                score_this_instance = (1 + (capvalue - performance_this_instance)
                                       / (num_instances * num_solvers * capvalue + 1))
            else:
                score_this_instance = 0
        else:
            # QUALITY_ABSOLUTE
            capvalue = capvalue_list[instance_idx]
            performance_this_instance, flag_successfully_solving = (
                compute_actual_performance_for_instance(
                    actual_portfolio_selector_path, instance, feature_data_csv_path,
                    performance_data_csv))

            if flag_successfully_solving:
                score_this_instance = performance_this_instance / capvalue
            else:
                score_this_instance = 0

        actual_selector_performance = actual_selector_performance + score_this_instance

    return actual_selector_performance


def compute_actual_performance_for_instance(
        actual_portfolio_selector_path: str,
        instance: str,
        feature_data_csv_path: str,
        performance_data_csv: SparklePerformanceDataCSV) -> tuple[float, bool]:
    """Return the total time of the selector on a given instance.

    Args:
      actual_portfolio_selector_path: Path to the portfolio selector.
      instance: Instance name.
      feature_data_csv_path: Path to the CSV file with the feature data.
      performance_data_csv: SparklePerformanceDataCSV object that holds the
        performance data.

    Returns:
      A 2-tuple where the first entry is the numeric performance value and
      the second entry is a Boolean indicating whether the instance was solved
      to optimality within the cutoff time.
    """
    feature_data_csv = sfdcsv.SparkleFeatureDataCSV(feature_data_csv_path)
    list_predict_schedule = get_list_predict_schedule(actual_portfolio_selector_path,
                                                      feature_data_csv, instance)
    performance_this_instance = 0
    flag_successfully_solving = True

    for i in range(0, len(list_predict_schedule)):
        solver = list_predict_schedule[i][0]
        performance = performance_data_csv.get_value(instance, solver)

        # Take best performance from the scheduled solvers
        if performance > performance_this_instance:
            performance_this_instance = performance

    return performance_this_instance, flag_successfully_solving


def compute_actual_used_time_for_instance(
        actual_portfolio_selector_path: str,
        instance: str,
        feature_data_csv_path: str,
        performance_data_csv: SparklePerformanceDataCSV) -> tuple[float, bool]:
    """Return the best performance of the solver schedule on a given instance.

    Args:
      actual_portfolio_selector_path: Path to the portfolio selector.
      instance: Instance name.
      feature_data_csv_path: Path to the CSV file with the feature data.
      performance_data_csv: SparklePerformanceDataCSV object that holds the
        performance data.

    Returns:
      A 2-tuple where the first entry is the time used  value and
      the second entry is a Boolean indicating whether the instance was solved
      to optimality within the cutoff time.
    """
    feature_data_csv = sfdcsv.SparkleFeatureDataCSV(feature_data_csv_path)
    list_predict_schedule = get_list_predict_schedule(actual_portfolio_selector_path,
                                                      feature_data_csv, instance)
    cutoff_time = sgh.settings.get_general_target_cutoff_time()
    used_time_for_this_instance = 0
    flag_successfully_solving = False

    for i in range(0, len(list_predict_schedule)):
        if used_time_for_this_instance >= cutoff_time:
            flag_successfully_solving = False
            break

        solver = list_predict_schedule[i][0]
        scheduled_cutoff_time_this_run = list_predict_schedule[i][1]
        required_time_this_run = performance_data_csv.get_value(instance, solver)

        if required_time_this_run <= scheduled_cutoff_time_this_run:
            used_time_for_this_instance = (
                used_time_for_this_instance + required_time_this_run)
            if used_time_for_this_instance > cutoff_time:
                flag_successfully_solving = False
            else:
                flag_successfully_solving = True
            break
        else:
            used_time_for_this_instance = (
                used_time_for_this_instance + scheduled_cutoff_time_this_run)
            continue

    return used_time_for_this_instance, flag_successfully_solving


def compute_actual_selector_marginal_contribution(
        performance_data_csv_path: str = sgh.performance_data_csv_path,
        feature_data_csv_path: str = sgh.feature_data_csv_path,
        flag_recompute: bool = False) -> list[tuple[str, float]]:
    """Compute the marginal contributions of solvers in the selector.

    Args:
      performance_data_csv: SparklePerformanceDataCSV object that holds the
        performance data.
      feature_data_csv_path: Path to the CSV file with the feature data.
      flag_recompute: Boolean indicating whether marginal contributions should
        be recalculated even if they already exist in a file. Defaults to False.

    Returns:
      A list of 2-tuples where every 2-tuple is of the form
      (solver name, marginal contribution).
    """
    actual_margi_cont_path = sgh.sparkle_marginal_contribution_actual_path

    # If the marginal contribution already exists in file, read it and return
    if not flag_recompute and actual_margi_cont_path.is_file():
        print("Marginal contribution for the actual selector already computed, reading "
              "from file instead! Use --recompute to force recomputation.")
        rank_list = read_marginal_contribution_csv(actual_margi_cont_path)

        return rank_list

    cutoff_time_str = str(sgh.settings.get_general_target_cutoff_time())
    print(f"In this calculation, cutoff time for each run is {cutoff_time_str} seconds")

    rank_list = []

    # Get values from CSV while all solvers and instances are included
    performance_data_csv = spdcsv.SparklePerformanceDataCSV(performance_data_csv_path)
    num_instances = performance_data_csv.get_row_size()
    num_solvers = performance_data_csv.get_column_size()
    capvalue_list = get_capvalue_list(performance_data_csv)

    if not Path("Tmp/").exists():
        Path("Tmp/").mkdir()

    # Compute performance of actual selector
    print("Computing actual performance for portfolio selector with all solvers ...")
    actual_portfolio_selector_path = sgh.sparkle_algorithm_selector_path
    scps.construct_sparkle_portfolio_selector(actual_portfolio_selector_path,
                                              performance_data_csv_path,
                                              feature_data_csv_path)

    if not Path(actual_portfolio_selector_path).exists():
        print(f"****** WARNING: {actual_portfolio_selector_path} does not exist! ******")
        print("****** WARNING: AutoFolio constructing the actual portfolio selector with"
              " all solvers failed! ******")
        print("****** WARNING: Using virtual best performance instead of actual "
              "performance for this portfolio selector! ******")
        virtual_best_performance = (
            performance_data_csv.calc_virtual_best_performance_of_portfolio(
                num_instances, num_solvers, capvalue_list))
        actual_selector_performance = virtual_best_performance
    else:
        actual_selector_performance = (
            compute_actual_selector_performance(
                actual_portfolio_selector_path, performance_data_csv_path,
                feature_data_csv_path, num_instances, num_solvers, capvalue_list))

    print("Actual performance for portfolio selector with all solvers is "
          f"{str(actual_selector_performance)}")
    print("Computing done!")

    # Compute contribution per solver
    for solver in performance_data_csv.list_columns():
        solver_name = sfh.get_last_level_directory_name(solver)
        print("Computing actual performance for portfolio selector excluding solver "
              f"{solver_name} ...")
        tmp_performance_data_csv = (
            spdcsv.SparklePerformanceDataCSV(performance_data_csv_path))
        tmp_performance_data_csv.delete_column(solver)
        tmp_performance_data_csv_file = (
            f"tmp_performance_data_csv_without_{solver_name}_"
            f"{sparkle_basic_help.get_time_pid_random_string()}.csv")
        tmp_performance_data_csv_path = (
            str(Path(sl.caller_log_dir / tmp_performance_data_csv_file)))
        sl.add_output(tmp_performance_data_csv_path,
                      "[written] Temporary performance data")
        tmp_performance_data_csv.save_csv(tmp_performance_data_csv_path)
        tmp_actual_portfolio_selector_path = (
            "Tmp/tmp_actual_portfolio_selector_"
            f"{sparkle_basic_help.get_time_pid_random_string()}")
        tmp_actual_portfolio_selector_path = (
            sgh.sparkle_algorithm_selector_dir / f"without_{solver_name}"
            / f"{sgh.sparkle_algorithm_selector_name}")

        if len(tmp_performance_data_csv.list_columns()) >= 1:
            scps.construct_sparkle_portfolio_selector(
                tmp_actual_portfolio_selector_path, tmp_performance_data_csv_path,
                feature_data_csv_path)
        else:
            print("****** WARNING: No solver exists ! ******")

        if not Path(tmp_actual_portfolio_selector_path).exists():
            print(f"****** WARNING: {tmp_actual_portfolio_selector_path} does not exist!"
                  " ******")
            print("****** WARNING: AutoFolio constructing the actual portfolio selector "
                  f"excluding solver {solver_name} failed! ******")
            print("****** WARNING: Using virtual best performance instead of actual "
                  "performance for this portfolio selector! ******")
            tmp_virtual_best_performance = (
                tmp_performance_data_csv.calc_virtual_best_performance_of_portfolio(
                    num_instances, num_solvers, capvalue_list))
            tmp_actual_selector_performance = tmp_virtual_best_performance
        else:
            tmp_actual_selector_performance = (
                compute_actual_selector_performance(
                    tmp_actual_portfolio_selector_path, tmp_performance_data_csv_path,
                    feature_data_csv_path, num_instances, num_solvers, capvalue_list))

        print(f"Actual performance for portfolio selector excluding solver {solver_name}"
              f" is {str(tmp_actual_selector_performance)}")
        os.system("rm -f " + tmp_performance_data_csv_path)
        sl.add_output(tmp_performance_data_csv_path,
                      "[removed] Temporary performance data")
        print("Computing done!")

        marginal_contribution = (
            actual_selector_performance - tmp_actual_selector_performance)

        solver_tuple = (solver, marginal_contribution)
        rank_list.append(solver_tuple)
        print(f"Marginal contribution (to Actual Selector) for solver {solver_name} is "
              f"{str(marginal_contribution)}")

    rank_list.sort(key=lambda marginal_contribution: marginal_contribution[1],
                   reverse=True)

    # Write actual selector contributions to file
    write_marginal_contribution_csv(actual_margi_cont_path, rank_list)

#    os.system(r'rm -f ' + actual_portfolio_selector_path)
    return rank_list


def print_rank_list(rank_list: list, mode: int) -> None:
    """Print the solvers ranked by marginal contribution.

    Args:
      rank_list: A list of 2-tuples as returned by function
        compute_actual_selector_marginal_contribution of the form
        (solver name, marginal contribution).
      mode: This integer parameter determines the reference for the solver ranking.
         Available options are 1 for 'perfect selector' and 2 for
         'actual selector'.
    """
    reference_selector = ""
    if mode == 1:
        reference_selector = "perfect selector"
    elif mode == 2:
        reference_selector = "actual selector"

    print("******")
    print("Solver ranking list via marginal contribution (Margi_Contr) with regards to "
          f"{reference_selector}")
    for i in range(0, len(rank_list)):
        solver = rank_list[i][0]
        marginal_contribution = rank_list[i][1]
        print(f"#{str(i+1)}: {sfh.get_last_level_directory_name(solver)}\t Margi_Contr: "
              f"{str(marginal_contribution)}")
    print("******")


def compute_perfect(flag_recompute: bool = False) -> list[tuple[str, float]]:
    """Compute the marginal contribution for the perfect portfolio selector.

    Args:
        flag_recompute: Flag indicating whether marginal contributions
            should be recalculated.

    Returns:
        rank_list: A list of 2-tuples of the form (solver name, marginal contribution).
    """
    print(
        "Start computing each solver's marginal contribution to perfect selector ..."
    )
    rank_list = compute_perfect_selector_marginal_contribution(
        flag_recompute=flag_recompute
    )
    print_rank_list(rank_list, 1)
    print("Marginal contribution (perfect selector) computing done!")

    return rank_list


def compute_actual(flag_recompute: bool = False) -> list[tuple[str, float]]:
    """Compute the marginal contribution for the actual portfolio selector.

    Args:
        flag_recompute: Flag indicating whether marginal contributions
            should be recalculated.

    Returns:
        rank_list: A list of 2-tuples of the form (solver name, marginal contribution).
    """
    print(
        "Start computing each solver's marginal contribution to actual selector ..."
    )
    rank_list = compute_actual_selector_marginal_contribution(
        flag_recompute=flag_recompute
    )
    print_rank_list(rank_list, 2)
    print("Marginal contribution (actual selector) computing done!")

    return rank_list


def compute_marginal_contribution(
        flag_compute_perfect: bool, flag_compute_actual: bool,
        flag_recompute: bool) -> None:
    """Compute the marginal contribution.

    Args:
        flag_compute_perfect: Flag indicating if the contribution for the perfect
            portfolio selector should be computed.
        flag_compute_actual: Flag indicating if the contribution for the actual portfolio
             selector should be computed.
        flag_recompute: Flag indicating whether marginal contributions
            should be recalculated.
    """
    if flag_compute_perfect:
        compute_perfect(flag_recompute)
    elif flag_compute_actual:
        compute_actual(flag_recompute)
    else:
        print("ERROR: compute_marginal_contribution called without a flag set to"
              " True, stopping execution")
        sys.exit()
