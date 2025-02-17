#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper functions for the execution of a parallel portfolio."""
import shutil
import os
import subprocess
import datetime
import fcntl
import glob
import sys
import time
from pathlib import Path
from pathlib import PurePath

import runrunner as rrr
from runrunner.base import Runner

from sparkle.platform import file_help as sfh
import global_variables as sgh
import sparkle_logging as slog
from sparkle.platform import slurm_help as ssh
from sparkle.platform.settings_help import ProcessMonitoring
from sparkle.types.objective import PerformanceMeasure
from CLI.help.command_help import CommandName

import functools
print = functools.partial(print, flush=True)


def jobtime_to_seconds(jobtime: str) -> int:
    """Convert a jobtime string to an integer number of seconds.

    Args:
        jobtime: Running time of a job in squeue (Slurm) format.

    Returns:
        An int indicating the number of seconds.
    """
    seconds = int(sum(int(x) * 60 ** i for i, x in enumerate(
        reversed(jobtime.split(":")))))

    return seconds


def add_log_statement_to_file(log_file: str, line: str, jobtime: str) -> None:
    """Log the starting time, end time and job number to a given file.

    Args:
        log_file: Path to the log file.
        line: A str of the form "sleep {str(sleep_time)}; scancel {str(jobid)}"
        jobtime: Running time of a job in squeue (Slurm) format.
    """
    now = datetime.datetime.now()
    job_duration_seconds = jobtime_to_seconds(jobtime)
    job_running_time = datetime.timedelta(seconds=job_duration_seconds)

    if line.rfind(";") != -1:
        sleep_seconds = line[:line.rfind(";")]
        sleep_seconds = int(sleep_seconds[sleep_seconds.rfind(" ") + 1:])
        now = now + datetime.timedelta(seconds=sleep_seconds)
        job_running_time = job_running_time + datetime.timedelta(seconds=sleep_seconds)
        job_nr = line[line.rfind(";") + 2:]
    else:
        # TODO: Not sure what the intend of checking job numbers in this function was.
        #       Writing a warning as job_nr for now, since this is a logging function,
        #       this issue should be of no harm to the functionality.
        job_nr = "WARNING: No job_nr found in function add_log_statement_to_file"

    current_time = now.strftime("%H:%M:%S")
    job_starting_time = now - job_running_time
    start_time_formatted = job_starting_time.strftime("%H:%M:%S")

    with Path(log_file).open("a+") as outfile:
        fcntl.flock(outfile.fileno(), fcntl.LOCK_EX)
        outfile.write(f"starting time: {start_time_formatted} end time: {current_time} "
                      f"job number: {job_nr}\n")


def log_computation_time(log_file: str, job_nr: str, job_duration: str) -> None:
    """Log the job number and job duration.

    Args:
        log_file: Path to the log file.
        job_nr: Job number as str.
        job_duration: Job duration as str.
    """
    if ":" in job_duration:
        job_duration = str(jobtime_to_seconds(job_duration))

    if "_" in job_nr:
        job_nr = job_nr[job_nr.rfind("_") + 1:]

    with Path(log_file).open("a+") as outfile:
        fcntl.flock(outfile.fileno(), fcntl.LOCK_EX)
        outfile.write(f"{job_nr}:{job_duration}\n")


def remove_temp_files_unfinished_solvers(solver_instance_list: list[str],
                                         sbatch_script_path: Path,
                                         temp_solvers: list[str]) -> None:
    """Remove temporary files and directories, and move result files.

    Args:
        solver_instance_list: List of solver instances.
        sbatch_script_path: Path to the sbatch script.
        temp_solvers: A list of temporary solvers.
    """
    tmp_dir = sgh.sparkle_tmp_path

    # Removes statusinfo files
    for solver_instance in solver_instance_list:
        shutil.rmtree(f"{sgh.pap_sbatch_tmp_path}/{solver_instance}", ignore_errors=True)

    # Removes the generated sbatch files
    sbatch_script_path.unlink()

    # Removes the directories generated for the solver instances
    for temp_solver in temp_solvers:
        for directories in os.listdir(tmp_dir):
            directories_path = f"{tmp_dir}{directories}"

            for solver_instance in solver_instance_list:
                if (Path(directories_path).is_dir()
                        and directories.startswith(
                            solver_instance[:len(temp_solver) + 1])):
                    shutil.rmtree(directories_path)

    # Removes or moves all remaining files
    list_of_paths = os.listdir(tmp_dir)
    to_be_deleted = list()
    to_be_moved = list()

    for file in list_of_paths:
        file_path = f"{tmp_dir}{file}"

        if not Path(file_path).is_dir():
            tmp_file = file[:file.rfind(".")]
            tmp_file = f"{tmp_file}.val"

            if tmp_file not in list_of_paths:
                to_be_deleted.append(file)
            else:
                to_be_moved.append(file)

    for file in to_be_deleted:
        Path(f"{tmp_dir}{file}").unlink(missing_ok=True)

    for file in to_be_moved:
        if ".val" in file:
            path_from = f"{tmp_dir}{file}"
            path_to = f"{str(sgh.pap_performance_data_tmp_path)}/{file}"

            try:
                shutil.move(path_from, path_to)
            except shutil.Error:
                print(f"the {str(sgh.pap_performance_data_tmp_path)} directory already "
                      "contains a file with the same name, it will be skipped")
            Path(path_from).unlink(missing_ok=True)


def find_finished_time_finished_solver(solver_instance_list: list[str],
                                       finished_job_array_nr: str) -> str:
    """Return the time at which a solver finished.

    If there is a solver that ended but did not make a result file this means that it
    was manually cancelled or it gave an error the template will ensure that all
    solver on that instance will be cancelled.
    Args:
        solver_instance_list: List of solver instances.
        finished_job_array_nr: The Slurm array number of the finished job.

    Returns:
        A formatted string that represents the finishing time of a solver.
    """
    time_in_format_str = "-1:00"
    solutions_dir = sgh.pap_performance_data_tmp_path
    results = sfh.get_list_all_extensions(solutions_dir, "result")

    for result in results:
        if "_" in finished_job_array_nr:
            finished_job_array_nr = finished_job_array_nr[
                finished_job_array_nr.rfind("_") + 1:]

        if result.startswith(solver_instance_list[int(finished_job_array_nr)]):
            result_file_path = solutions_dir / result

            with result_file_path.open("r") as result_file:
                result_lines = result_file.readlines()
                result_time = int(float(result_lines[2].strip()))
                time_in_format_str = str(datetime.timedelta(seconds=result_time))

    return time_in_format_str


def cancel_remaining_jobs(logging_file: str, job_id: str,
                          finished_solver_id_list: list[str],
                          portfolio_size: int, solver_instance_list: list[str],
                          pending_job_with_new_cutoff: dict[str, int] = {}
                          ) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Cancel jobs past the cutoff, update cutoff time for jobs that should continue.

    Args:
        logging_file: Path to the logging file.
        job_id: Job ID as str.
        finished_solver_id_list: List of str typed job IDs of finished solvers.
        portfolio_size: Size of parallel algorithm portfolio.
        solver_instance_list: List of solver instances as str.
        pending_job_with_new_cutoff: Dict with jobid str as key, and cutoff_seconds int
            as value. Defaults to an empty dict.

    Returns:
        remaining_jobs: A dict containing a jobid str as key, and a (two
            element) list of str with the jobtime and jobstatus.
        pending_job_with_new_cutoff: A dict of pending jobs with new cutoff time
            (jobid str as key, and cutoff_seconds int as value).
    """
    # Find all job_array_numbers that are currently running
    # This is specific to Slurm
    result = subprocess.run(["squeue", "--array", "--jobs", job_id,
                             "--format", "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R"],
                            capture_output=True, text=True)
    remaining_jobs = {}

    for jobs in result.stdout.strip().split("\n"):
        jobid = jobs.strip().split()[0]  # First squeue column is JOBID
        jobtime = jobs.strip().split()[5]  # Sixth squeue column is TIME
        jobstatus = jobs.strip().split()[4]  # Fifth squeue column is ST (status)

        # If option extended is used some jobs are not directly cancelled to allow all
        # jobs to compute for at least the same running time.
        if (sgh.settings.get_paraport_process_monitoring()
                == ProcessMonitoring.EXTENDED):
            # If a job in a portfolio with a finished solver starts running its timelimit
            # needs to be updated.
            if jobid in pending_job_with_new_cutoff and jobstatus == "R":
                current_seconds = jobtime_to_seconds(jobtime)
                sleep_time = pending_job_with_new_cutoff[jobid] - current_seconds
                command_line = f"sleep {str(sleep_time)}; scancel {str(jobid)}"
                add_log_statement_to_file(logging_file, command_line, jobtime)
                pending_job_with_new_cutoff.pop(jobid)

        if jobid.startswith(str(job_id)):
            remaining_jobs[jobid] = [jobtime, jobstatus]

    for job in remaining_jobs:
        # Update all jobs in the same array segment as the finished job with its
        # finishing time
        for finished_solver_id in finished_solver_id_list:
            # if job in the same array segment
            if (int(int(job[job.find("_") + 1:]) / portfolio_size)
                    == int(int(finished_solver_id) / portfolio_size)):
                # If option extended is used some jobs are not directly cancelled to
                # allow all jobs to compute for at least the same running time.
                if (sgh.settings.get_paraport_process_monitoring()
                        == ProcessMonitoring.EXTENDED):
                    # Update the cutofftime of the to be cancelled job, if job if
                    # already past that it automatically stops.
                    new_cutoff_time = find_finished_time_finished_solver(
                        solver_instance_list, finished_solver_id)
                    current_seconds = jobtime_to_seconds(remaining_jobs[job][0])
                    cutoff_seconds = jobtime_to_seconds(new_cutoff_time)
                    actual_cutofftime = sgh.settings.get_general_target_cutoff_time()

                    if (remaining_jobs[job][1] == "R"
                            and int(cutoff_seconds) < int(actual_cutofftime)):
                        if int(current_seconds) < int(cutoff_seconds):
                            sleep_time = int(cutoff_seconds) - int(current_seconds)
                            command_line = f"sleep {str(sleep_time)}; scancel {str(job)}"
                            add_log_statement_to_file(logging_file, command_line,
                                                      remaining_jobs[job][0])
                        else:
                            command_line = f"scancel {str(job)}"
                            add_log_statement_to_file(logging_file, command_line,
                                                      remaining_jobs[job][0])
                            logging_file2 = (
                                f'{logging_file[:logging_file.rfind(".")]}2.txt')
                            log_computation_time(logging_file2, job, cutoff_seconds)
                        # Shell is needed for admin rights to do scancel
                        subprocess.Popen(command_line, shell=True)  # noqa # nosec
                    else:
                        pending_job_with_new_cutoff[job] = cutoff_seconds
                else:
                    command_line = f"scancel {str(job)}"
                    add_log_statement_to_file(logging_file, command_line,
                                              remaining_jobs[job][0])
                    logging_file2 = logging_file[:logging_file.rfind(".")] + "2.txt"
                    log_computation_time(logging_file2, job, "-1")
                    # Shell is needed for admin rights to do scancel
                    subprocess.Popen(command_line, shell=True)  # noqa # nosec

    return remaining_jobs, pending_job_with_new_cutoff


def wait_for_finished_solver(
        logging_file: str,
        job_id: str,
        solver_instance_list: list[str],
        remaining_job_dict: dict[str, list[str]],
        pending_job_with_new_cutoff: dict[str, int],
        started: bool,
        portfolio_size: int) -> tuple[list[str], dict[str, int], bool]:
    """Wait for a solver to finish, then return which finished and which may still run.

    Args:
        logging_file: Path to the logging file.
        job_id: Job ID as string.
        solver_instance_list: List of solver instances.
        remaining_job_dict: Dict of remaining jobs (jobid str as key, and a list of str
            as value).
        pending_job_with_new_cutoff: Dict of pending jobs with new cutoff time
            (jobid str as key, and cutoff_seconds int as value).
        started: Boolean indicating whether the portfolio has started running.
        portfolio_size: Size of the portfolio.

    Returns:
        finished_solver_list: A list of str typed job IDs of finished solvers.
        pending_job_with_new_cutoff: A dict with jobid str as key, and cutoff_seconds int
            as value.
        started: A bool indicating whether the PAP (parallel algorithm portfolio) has
            started running.
    """
    number_of_solvers = len(remaining_job_dict) if remaining_job_dict else portfolio_size
    n_seconds = 1
    done = False
    # TODO: Fix weird situation. This starts as dict, later becomes a list...
    current_solver_list = remaining_job_dict
    finished_solver_list = list()
    # TODO: This while loop is rather lengthy and chaotic. This should be refactored.
    # Especially the output string handling of the subprocess should be more structured.
    while not done:
        # Ask the cluster for a list of all jobs which are currently running
        result = subprocess.run(["squeue", "--array", "--jobs", job_id,
                                 "--format", "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R"],
                                capture_output=True, text=True)

        # If none of the jobs on the cluster are running then nothing has to done yet,
        # check back in n_seconds
        if " R " not in str(result):
            if len(result.stdout.strip().split("\n")) == 1:
                done = True  # No jobs are remaining
                break

            time.sleep(n_seconds)  # No jobs have started yet;
        # If the results are less than the number of solvers then this means that there
        # are finished solvers(+1 becuase of the header of results)
        elif len(result.stdout.strip().split("\n")) < (1 + number_of_solvers):
            if started is False:  # Log starting time
                now = datetime.datetime.now()
                current_time = now.strftime("%H:%M:%S")

                with Path(logging_file).open("a+") as outfile:
                    fcntl.flock(outfile.fileno(), fcntl.LOCK_EX)
                    outfile.write(f"starting time of portfolio: {current_time}\n")

                started = True

            unfinished_solver_list = list()

            for jobs in result.stdout.strip().split("\n"):
                jobid = jobs.strip().split()[0]

                if jobid.startswith(job_id):
                    unfinished_solver_list.append(jobid[jobid.find("_") + 1:])

            finished_solver_list = [item for item in current_solver_list
                                    if item not in unfinished_solver_list]

            for finished_solver in finished_solver_list:
                new_cutoff_time = find_finished_time_finished_solver(
                    solver_instance_list, finished_solver)

                if new_cutoff_time != "-1:00":
                    log_statement = (f"{finished_solver} finished succesfully or "
                                     "has reached the cutoff time")
                    add_log_statement_to_file(logging_file, log_statement,
                                              str(new_cutoff_time))
                    logging_file2 = logging_file[:logging_file.rfind(".")] + r"2.txt"
                    log_computation_time(logging_file2, finished_solver, new_cutoff_time)

            done = True
        # No jobs have finished but some jobs are running
        else:
            if started is False:  # Log starting time
                now = datetime.datetime.now()
                current_time = now.strftime("%H:%M:%S")

                with Path(logging_file).open("a+") as outfile:
                    fcntl.flock(outfile.fileno(), fcntl.LOCK_EX)
                    outfile.write(f"starting time of portfolio: {current_time}\n")

                started = True

            time.sleep(n_seconds)
            current_solver_list = list()

            # Check if the running jobs are from a portfolio which contain an already
            # finished solver
            for jobs in result.stdout.strip().split("\n"):
                jobid = jobs.strip().split()[0]
                jobtime = jobs.strip().split()[5]
                jobstatus = jobs.strip().split()[4]

                # If option extended is used some jobs are not directly cancelled to
                # allow all jobs to compute for at least the same running time.
                if (sgh.settings.get_paraport_process_monitoring()
                        == ProcessMonitoring.EXTENDED):
                    if jobid in pending_job_with_new_cutoff and jobstatus == "R":
                        # Job is in a portfolio with a solver that already has finished
                        # and has to be cancelled in the finishing time of that solver
                        current_seconds = jobtime_to_seconds(jobtime)
                        sleep_time = pending_job_with_new_cutoff[jobid] - current_seconds
                        command_line = f"sleep {str(sleep_time)}; scancel {str(jobid)}"
                        add_log_statement_to_file(logging_file, command_line, jobtime)
                        pending_job_with_new_cutoff.pop(jobid)

                if (jobid.startswith(job_id)):
                    # add the job to the current solver list
                    current_solver_list.append(jobid[jobid.find("_") + 1:])

    return finished_solver_list, pending_job_with_new_cutoff, started


def handle_waiting_and_removal_process(
        instances: list[str],
        logging_file: str,
        job_id: str,
        solver_instance_list: list[str],
        sbatch_script_path: Path,
        portfolio_size: int,
        remaining_job_dict: dict[str, list[str]] = dict(),
        finished_instances_dict: dict[str, list[str, int]] = dict(),
        pending_job_with_new_cutoff: dict[str, int] = dict(),
        started: bool = False) -> bool:
    """Wait for solvers to finish running, and clean up after them.

    Args:
        instances: A list of instances.
        logging_file: Path to the logging file.
        job_id: Job ID as string.
        solver_instance_list: A list of solver instances.
        sbatch_script_path: Path to sbatch script.
        portfolio_size: Size of the portfolio.
        remaining_job_dict: A dictionary of remaining jobs. Defaults to None.
        finished_instances_dict: A dictionary of finished instances. Defaults to None.
        pending_job_with_new_cutoff: A dictionary of pending jobs with new cutoff time.
            Defaults to None.
        started: A boolean value indicating whether the process has started. Defaults to
            False.

    Returns:
        True on success, may stop program execution early for failure.
    """
    if len(remaining_job_dict) > 0:
        print(f"A job has ended, remaining jobs = {str(len(remaining_job_dict))}")

    if not finished_instances_dict:
        for instance in instances:
            finished_instances_dict[Path(instance).name] = ["UNSOLVED", 0]

    perf_data_tmp_path = sgh.pap_performance_data_tmp_path

    # For each finished instance
    for instance in finished_instances_dict:
        # Only look at solvers for this instance
        current_sol_inst_list = [si for si in solver_instance_list if instance in si]
        # Check results for each solver
        for solver_instance in current_sol_inst_list:
            finished_solver_files = glob.glob(f"{str(perf_data_tmp_path)}/*"
                                              f"{solver_instance}*result")

            # If there is more than one result file for this solver-instance combination
            # something went wrong (probably during cleanup).
            if len(finished_solver_files) > 1:
                print(f"ERROR: {str(len(finished_solver_files))} result files found for"
                      f" {solver_instance} while there should be only one!")
                sys.exit(-1)

            for finished_solver_file in finished_solver_files:
                file_path = finished_solver_file

                with Path(file_path).open("r") as infile:
                    content = infile.readlines()

                solving_time = float(content[2].strip())

                # A new instance is solved
                if (finished_instances_dict[instance][1] == float(0)):
                    finished_instances_dict[instance][1] = solving_time

                    if (solving_time
                            > float(sgh.settings.get_general_target_cutoff_time())):
                        print(f"{str(instance)} has reached the cutoff time without "
                              "being solved.")
                    else:
                        print(f"{str(instance)} has been solved in "
                              f"{str(solving_time)} seconds!")

                        temp_files = glob.glob(f"{sgh.sparkle_tmp_path}{solver_instance}"
                                               f"*.rawres")

                        for rawres_file_path in temp_files:
                            with Path(rawres_file_path).open("r") as rawres_file:
                                raw_content = rawres_file.readlines()

                            nr_of_lines_raw_content = len(raw_content)

                            for lines in range(nr_of_lines_raw_content):
                                if "\ts " in raw_content[
                                        nr_of_lines_raw_content - lines - 1]:
                                    results_line = raw_content[
                                        nr_of_lines_raw_content - lines - 1]
                                    print("result = " + str(results_line[
                                        results_line.find("s") + 2:].strip()))
                                    finished_instances_dict[instance][0] = str(
                                        results_line[results_line.find("s") + 2:].strip()
                                    )
                                    break

                # A solver has an improved performance time on an instance
                elif (float(finished_instances_dict[instance][1]) > solving_time):
                    finished_instances_dict[instance][1] = solving_time
                    print(f"{str(instance)} has been solved with an improved solving "
                          f"time of {str(solving_time)} seconds!")

    # Monitors the running jobs waiting for a solver that finishes
    finished_solver_id_list, pending_job_with_new_cutoff, started = (
        wait_for_finished_solver(
            logging_file, job_id, solver_instance_list, remaining_job_dict,
            pending_job_with_new_cutoff, started, portfolio_size))

    # Handles the updating of all jobs within the portfolios of which contain a finished
    # job
    remaining_job_dict, pending_job_with_new_cutoff = cancel_remaining_jobs(
        logging_file, job_id, finished_solver_id_list, portfolio_size,
        solver_instance_list, pending_job_with_new_cutoff)

    # If there are still unfinished jobs recursively handle the remaining jobs.
    if len(remaining_job_dict) > 0:
        handle_waiting_and_removal_process(instances, logging_file, job_id,
                                           solver_instance_list, sbatch_script_path,
                                           portfolio_size, remaining_job_dict,
                                           finished_instances_dict,
                                           pending_job_with_new_cutoff, started)

    return True


def remove_result_files(instances: list[str]) -> None:
    """Remove existing results for given instances.

    Args:
        instances: List of instance names.
    """
    for instance in instances:
        instance = Path(instance).name
        pap_files = [f for f in sgh.pap_performance_data_tmp_path.iterdir()
                     if f"_{instance}_" in str(f)]
        tmp_files = [f for f in Path(sgh.sparkle_tmp_path).iterdir()
                     if f"_{instance}_" in str(f)]
        sfh.rmfiles(pap_files + tmp_files)


def run_parallel_portfolio(instances: list[str],
                           portfolio_path: Path,
                           run_on: Runner = Runner.SLURM) -> bool:
    """Run the parallel algorithm portfolio and return whether this was successful.

    Args:
        instances: List of instance names.
        portfolio_path: Path to the parallel portfolio.

    Returns:
        True if successful; False otherwise.
    """
    # Remove existing result files
    remove_result_files(instances)
    solver_list = sfh.get_solver_list_from_parallel_portfolio(portfolio_path)

    performance_measure =\
        sgh.settings.get_general_sparkle_objectives()[0].PerformanceMeasure
    parameters = []
    num_jobs = len(solver_list) * len(instances)
    temp_solvers = []
    solver_instance_list = []
    # Create a command for each instance-solver combination
    for instance_path in instances:
        instance_name = Path(instance_path).name
        for solver_path in solver_list:
            seeds = []
            # If the solver has a seed range specified, create a call per seed
            if " " in solver_path:
                solver_path, _, seed_range = solver_path.strip().split()
                seed_range = int(seed_range)
                seeds = [seed_val for seed_val in range(1, seed_range + 1)]
                solver_name = Path(solver_path).name
                temp_solvers.append(f"{solver_name}_seed_")
                num_jobs += (seed_range - 1)
            else:
                solver_path = Path(solver_path)

            base_param = f"--instance {(instance_path)} --solver "\
                         f"{str(solver_path)} --performance-measure "\
                         f"{performance_measure.name}"
            if len(seeds) > 0:
                for seed_idx in seeds:
                    parameters.append(f"{base_param} --seed {seed_idx}")
                    solver_instance_list.append(
                        f"{solver_name}_seed_{str(seed_idx)}_{instance_name}")
            else:
                parameters.append(base_param)
                solver_instance_list.append(f"{solver_name}_{instance_name}")

    # Run the script and cancel the remaining solvers if a solver finishes before the
    # end of the cutoff_time
    file_path_output1 = str(PurePath(sgh.sparkle_global_output_dir / slog.caller_out_dir
                            / "Log/logging.txt"))
    sfh.create_new_empty_file(file_path_output1)
    srun_options = ["-N1", "-n1"] + ssh.get_slurm_options_list()
    parallel_jobs = min(sgh.settings.get_slurm_number_of_runs_in_parallel(), num_jobs)
    sbatch_options_list = ssh.get_slurm_options_list()
    # Create cmd list
    base_cmd_str = ("CLI/core/run_solvers_core.py --run-status-path "
                    f"{str(sgh.pap_sbatch_tmp_path)}")
    cmd_list = [f"{base_cmd_str} {params}" for params in parameters]

    # TODO: This try/except structure is absolutely massive.
    # This entire method should be refactored after everything works with RunRunner
    try:
        run = rrr.add_to_queue(
            runner=run_on,
            cmd=cmd_list,
            name=CommandName.RUN_SPARKLE_PARALLEL_PORTFOLIO,
            parallel_jobs=parallel_jobs,
            path="./",
            base_dir=sgh.sparkle_tmp_path,
            sbatch_options=sbatch_options_list,
            srun_options=srun_options)
        if run_on == Runner.LOCAL:
            run.wait()

        # NOTE: the IF statement below is Slurm only as well?
        # As running runtime based performance may be less relevant for Local
        # NOTE: Why does this command have its own waiting process? If we need to handle
        # Something after the job is done, we can just create a callback script to that
        perf_m = sgh.settings.get_general_sparkle_objectives()[0].PerformanceMeasure
        if (run_on == Runner.SLURM and perf_m == PerformanceMeasure.RUNTIME):
            handle_waiting_and_removal_process(instances, file_path_output1, run.run_id,
                                               solver_instance_list, run.script_filepath,
                                               num_jobs / len(instances))

            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M:%S")

            with Path(file_path_output1).open("a+") as outfile:
                fcntl.flock(outfile.fileno(), fcntl.LOCK_EX)
                outfile.write(f"ending time of portfolio: {current_time}\n")

            # After all jobs have finished remove/extract the files in temp only needed
            # for the running of the portfolios.
            remove_temp_files_unfinished_solvers(solver_instance_list,
                                                 run.script_filepath,
                                                 temp_solvers)
        elif run_on == Runner.SLURM:
            done = False
            wait_cutoff_time = False
            n_seconds = 4
            # TODO: This piece of code is quite identical to the loop in
            # wait_for_finished solver. Perhaps it can be merged.
            while not done:
                # Ask the cluster for a list of all jobs which are currently running
                result = subprocess.run(["squeue", "--array",
                                         "--jobs", run.run_id,
                                         "--format",
                                         "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R"],
                                        capture_output=True, text=True)

                # If none of the jobs on the cluster are running then nothing has to done
                # yet, check back in n_seconds
                if " R " not in str(result):
                    if len(result.stdout.strip().split("\n")) == 1:
                        done = True  # No jobs are remaining
                        break
                else:
                    # Wait until the last few seconds before checking often
                    if not wait_cutoff_time:
                        n_seconds = sgh.settings.get_general_target_cutoff_time() - 6
                        time.sleep(n_seconds)
                        wait_cutoff_time = True
                        n_seconds = 1  # Start checking often

                time.sleep(n_seconds)
        else:
            run.wait()

        finished_instances_dict = {}
        for instance in instances:
            instance = Path(instance).name
            finished_instances_dict[instance] = ["UNSOLVED", 0]

        tmp_res_files = glob.glob(f"{str(sgh.pap_performance_data_tmp_path)}/*.result")
        for finished_solver_files in tmp_res_files:
            for instance in finished_instances_dict:
                if str(instance) in str(finished_solver_files):
                    file_path = f"{str(finished_solver_files)}"

                    with Path(file_path).open("r") as infile:
                        content = infile.readlines()

                    # A new instance is solved
                    if (finished_instances_dict[instance][0] == "UNSOLVED"):
                        finished_instances_dict[instance][1] = float(content[2].strip())
                        finished_instances_dict[instance][0] = "SOLVED"
                    elif (float(finished_instances_dict[instance][1])
                            > float(content[2].strip())):
                        finished_instances_dict[instance][1] = float(content[2].strip())

        for instances in finished_instances_dict:
            if (finished_instances_dict[instances][0] == "SOLVED"
                    and float(finished_instances_dict[instances][1]) > 0):
                # To filter out constraint files
                if "e" not in str(finished_instances_dict[instances][1]):
                    print(f"{str(instances)} was solved with the result: "
                          f"{str(finished_instances_dict[instances][1])}")
            else:
                print(f"{str(instances)} was not solved in the given cutoff-time.")
    except Exception as except_msg:
        print(f"Exception thrown during {CommandName.RUN_SPARKLE_PARALLEL_PORTFOLIO}: "
              f"{except_msg}")
        return False

    return True
