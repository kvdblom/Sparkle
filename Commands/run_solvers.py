#!/usr/bin/env python3

import sys
import argparse
from typing import List
from pathlib import Path

from sparkle_help import sparkle_record_help as srh
from sparkle_help import sparkle_global_help as sgh
from sparkle_help import sparkle_performance_data_csv_help as spdcsv
from sparkle_help import sparkle_run_solvers_help as srs
from sparkle_help import sparkle_run_solvers_parallel_help as srsp
from sparkle_help import sparkle_job_parallel_help as sjph
from sparkle_help import sparkle_logging as sl
from sparkle_help import sparkle_settings
from sparkle_help.sparkle_settings import PerformanceMeasure
from sparkle_help.sparkle_settings import SolutionVerifier
from sparkle_help.sparkle_settings import SettingState
from sparkle_help import argparse_custom as ac
from sparkle_help.sparkle_command_help import CommandName

import runrunner as rrr


def run_solvers_on_instances(
        parallel: bool = True,
        recompute: bool = False,
        run_on: str = None,
        also_construct_selector_and_report: bool = False,
):
    """ Run all the solvers on all the instances that were not not previously run. If
        recompute, rerun everything even if previously run. Where the solvers are
        executed can be controlled with 'run_on'.

        Parameters
        ----------
        parallel: bool
            Run the solvers in parallel or one at a time. Default: True
        recompute: bool
            If True, recompute all solver-instance pair even if their were run before.
            Default: False
        run_on: str
            On which computer or clusters to execute the solvers.
            Available: local, slurm. Default: slurm
        also_construct_selector_and_report: bool
            If True, the selector will be constructed and a report will be produce
     """
    if recompute:
        spdcsv.Sparkle_Performance_Data_CSV(sgh.performance_data_csv_path).clean_csv()

    # Write used settings to file
    sgh.settings.write_used_settings()

    if parallel:
        num_job_in_parallel = sgh.settings.get_slurm_number_of_runs_in_parallel()
    else:
        num_job_in_parallel = 1

    # Run the solvers
    solver_jobs = srsp.running_solvers_parallel(
        performance_data_csv_path=sgh.performance_data_csv_path,
        num_job_in_parallel=num_job_in_parallel,
        recompute=recompute,
        run_on=run_on
    )

    # Update performance data csv after the last job is done
    if run_on == "local":

        last_job = merge_job = rrr.add_to_local_queue(
            cmd="Commands/sparkle_help/sparkle_csv_merge_help.py",
            depends=solver_jobs)

        if also_construct_selector_and_report:
            selector_job = rrr.add_to_local_queue(
                cmd="Commands/construct_sparkle_portfolio_selector.py",
                depends=merge_job)

            last_job = rrr.add_to_local_queue(
                cmd="Commands/generate_report.py",
                depends=selector_job)

        print(f"c Waiting for the calculations to finish.")
        last_job.wait()

    elif run_on == "slurm":
        csv_job = sjph.running_job_parallel(
            "Commands/sparkle_help/sparkle_csv_merge_help.py",
            solver_jobs, CommandName.RUN_SOLVERS
        )
        # TODO: Check output (files) for error messages, e.g.:
        # error: unrecognized arguments
        # srun: error:
        # TODO: Check performance data CSV for missing values

        # Only do selector construction and report generation if the flag is set;
        # Default behaviour is not to run them, like the sequential run_solvers command

        if also_construct_selector_and_report:
            jobs = [*solver_jobs, csv_job, construct_selector_and_report([csv_job])]
        else:
            jobs = [*solver_jobs, csv_job]

        print(f"c Running solvers in parallel. Waiting for Slurm job(s) with id(s): "
              f"{','.join(jobs)}")
    else:
        print(f"c {run_on} is not a valid computer/cluster target")


def construct_selector_and_report(dependency_jobid_list: List[str] = []):
    job_script = "Commands/construct_sparkle_portfolio_selector.py"
    run_job_parallel_jobid = sjph.running_job_parallel(
        job_script,
        dependency_jobid_list,
        CommandName.CONSTRUCT_SPARKLE_PORTFOLIO_SELECTOR,
    )

    if run_job_parallel_jobid:
        dependency_jobid_list.append(run_job_parallel_jobid)
    job_script = "Commands/generate_report.py"
    run_job_parallel_jobid = sjph.running_job_parallel(
        job_script, dependency_jobid_list, CommandName.GENERATE_REPORT
    )

    return run_job_parallel_jobid


if __name__ == r"__main__":
    # Initialise settings
    global settings
    sgh.settings = sparkle_settings.Settings()

    # Log command call
    sl.log_command(sys.argv)

    # Define command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="recompute the performance of all solvers on all instances",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="run the solver on multiple instances in parallel",
    )
    parser.add_argument(
        "--performance-measure",
        choices=PerformanceMeasure.__members__,
        help="the performance measure, e.g. runtime",
    )
    parser.add_argument(
        "--target-cutoff-time",
        type=int,
        help="cutoff time per target algorithm run in seconds",
    )
    parser.add_argument(
        "--also-construct-selector-and-report",
        action="store_true",
        help=("after running the solvers also construct the selector and generate"
              " the report"),
    )
    parser.add_argument(
        "--verifier",
        help=("problem specific verifier that should be used to verify solutions found"
              " by a target algorithm"),
    )

    parser.add_argument(
        "--run-on",
        default="slurm",
        help=("On which computer/cluster to execute the calculation." 
              "Available:  local, slurm. Default: slurm"),
    )

    parser.add_argument(
        "--settings-file",
        type=Path,
        help=("specify the settings file to use in case you want to use one other than"
              " the default"),
    )

    # Process command line arguments
    args = parser.parse_args()

    if args.settings_file is not None:
        sgh.settings.read_settings_ini(
            args.settings_file, SettingState.CMD_LINE
        )  # Do first, so other command line options can override settings from the file

    if args.performance_measure is not None:
        sgh.settings.set_general_performance_measure(
            PerformanceMeasure.from_str(args.performance_measure), SettingState.CMD_LINE
        )

    if args.verifier is not None:
        sgh.settings.set_general_solution_verifier(
            SolutionVerifier.from_str(args.verifier), SettingState.CMD_LINE
        )

    if args.target_cutoff_time:
        sgh.settings.set_general_target_cutoff_time(
            args.target_cutoff_time, SettingState.CMD_LINE
        )

    print("c Start running solvers ...")

    if not srh.detect_current_sparkle_platform_exists():
        print("c No Sparkle platform found; please first run the initialise command")
        exit()

    run_solvers_on_instances(
        parallel=args.parallel,
        recompute=args.recompute,
        also_construct_selector_and_report=args.also_construct_selector_and_report,
        run_on=args.run_on,
    )

