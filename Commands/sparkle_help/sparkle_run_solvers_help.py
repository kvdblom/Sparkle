#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

'''
Software: 	Sparkle (Platform for evaluating empirical algorithms/solvers)

Authors: 	Chuan Luo, chuanluosaber@gmail.com
			Holger H. Hoos, hh@liacs.nl

Contact: 	Chuan Luo, chuanluosaber@gmail.com
'''

import os
import time
import random
import sys
import fcntl
from pathlib import Path
from enum import Enum

try:
	from sparkle_help import sparkle_global_help as sgh
	from sparkle_help import sparkle_basic_help as sbh
	from sparkle_help import sparkle_file_help as sfh
	from sparkle_help import sparkle_performance_data_csv_help as spdcsv
	from sparkle_help import sparkle_experiments_related_help as ser
	from sparkle_help import sparkle_job_help as sjh
	from sparkle_help import sparkle_customized_config_help as scch
	from sparkle_help.sparkle_settings import PerformanceMeasure
	from sparkle_help.sparkle_settings import SolutionVerifier
except ImportError:
	import sparkle_global_help as sgh
	import sparkle_basic_help as sbh
	import sparkle_file_help as sfh
	import sparkle_performance_data_csv_help as spdcsv
	import sparkle_experiments_related_help as ser
	import sparkle_job_help as sjh
	import sparkle_customized_config_help as scch
	from sparkle_settings import PerformanceMeasure
	from sparkle_settings import SolutionVerifier

import functools
print = functools.partial(print, flush=True)


def get_solver_call_from_wrapper(solver_wrapper_path: str, instance_path: str) -> str:
	cmd_solver_call = ''

	cutoff_time_str = str(sgh.settings.get_general_target_cutoff_time())
	seed_str = str(sgh.get_seed())
	cmd_get_solver_call = solver_wrapper_path + ' --print-command \"' + instance_path + '\" --seed ' + seed_str + ' --cutoff-time ' + cutoff_time_str
	solver_call_rawresult = os.popen(cmd_get_solver_call)
	solver_call_result = solver_call_rawresult.readlines()[0].strip()

	if len(solver_call_result) > 0:
		cmd_solver_call = solver_call_result
	else:
		# TODO: Add instructions for the user that might fix the issue?
		print('c ERROR: Failed to get valid solver call command from wrapper at \'' + solver_wrapper_path + '\' stopping execution!')
		sys.exit()

	return cmd_solver_call


def run_solver_on_instance(relative_path, solver_wrapper_path: str, instance_path: str, raw_result_path, runsolver_values_path):
	cutoff_time_str = str(sgh.settings.get_general_target_cutoff_time())

	if not Path(solver_wrapper_path).is_file():
		print('c ERROR: Wrapper named \'' + solver_wrapper_path + '\' not found, stopping execution!')
		sys.exit()

	# Get the solver call command from the wrapper
	cmd_solver_call = get_solver_call_from_wrapper(solver_wrapper_path, instance_path)

	# Prepare runsolver call
	runsolver_path = sgh.runsolver_path
	runsolver_option = r'--timestamp --use-pty'
	cutoff_time_each_run_option = r'-C ' + cutoff_time_str
	runsolver_values_log = '-v ' + runsolver_values_path
	runsolver_watch_data_path = runsolver_values_path.replace('val', 'log')
	runsolver_watch_data_path_option = r'-w ' + runsolver_watch_data_path
	raw_result_path_option = r'-o ' + raw_result_path

	# Finalise command
	command_line_run_solver = runsolver_path + r' ' + runsolver_option + r' ' + cutoff_time_each_run_option + r' ' + runsolver_watch_data_path_option + r' ' + runsolver_values_log + r' ' + raw_result_path_option + r' ' + relative_path + '/' + cmd_solver_call

	# Execute command
	try:
		os.system(command_line_run_solver)
	except:
		# TODO: Replace by error? Why create an empty file if the command fails?
		if not os.path.exists(raw_result_path):
			sfh.create_new_empty_file(raw_result_path)

	#command_line = 'rm -f ' + runsolver_watch_data_path
	#os.system(command_line)

	return


def running_solvers(performance_data_csv_path, mode):
	cutoff_time_str = str(sgh.settings.get_general_target_cutoff_time())
	performance_measure = sgh.settings.get_general_performance_measure()
	performance_data_csv = spdcsv.Sparkle_Performance_Data_CSV(performance_data_csv_path)
	if mode == 1: list_performance_computation_job = performance_data_csv.get_list_remaining_performance_computation_job()
	elif mode == 2: list_performance_computation_job = performance_data_csv.get_list_recompute_performance_computation_job()
	else:
		print('c Running solvers mode error!')
		print('c Do not run solvers')
		sys.exit()
	
	print('c The cutoff time per algorithm run to solve an instance is set to ' + cutoff_time_str + ' seconds')
	
	total_job_num = sjh.get_num_of_total_job_from_list(list_performance_computation_job)
	current_job_num = 1
	print('c The total number of jobs to run is: ' + str(total_job_num))

	if total_job_num < 1:
		return
	
	for i in range(0, len(list_performance_computation_job)):
		instance_path = list_performance_computation_job[i][0]
		solver_list = list_performance_computation_job[i][1]
		len_solver_list = len(solver_list)
		for j in range(0, len_solver_list):
			solver_path = solver_list[j]
			
			raw_result_path = r'Tmp/' + sfh.get_last_level_directory_name(solver_path) + r'_' + sfh.get_last_level_directory_name(instance_path) + r'_' + sbh.get_time_pid_random_string() + r'.rawres'
			runsolver_values_path = raw_result_path.replace('.rawres', '.val')
			
			time.sleep(ser.sleep_time_after_each_solver_run)
			
			print('c')
			print('c Solver ' + sfh.get_last_level_directory_name(solver_path) + ' running on instance ' + sfh.get_last_level_directory_name(instance_path) + ' ...')

			solver_wrapper_path = solver_path + '/' + sgh.sparkle_run_default_wrapper
			run_solver_on_instance(solver_path, solver_wrapper_path, instance_path, raw_result_path, runsolver_values_path)
			runtime, quality, status = process_results(raw_result_path, solver_wrapper_path, runsolver_values_path)

			if status == 'CRASHED':
				print('c Warning: Solver ' + solver_path + ' appears to have crashed on instance ' + instance_path + ' for details see the solver log file at ' + raw_result_path)

			# Handle timeouts
			penalised_str = ''
			runtime, status = handle_timeouts(runtime, status)
			if performance_measure == PerformanceMeasure.RUNTIME and (status == 'TIMEOUT' or status == 'UNKNOWN'):
				penalised_str = ' (penalised)'

			status = verify(instance_path, raw_result_path, solver_path, status)

			# If status == 'WRONG' after verification remove solver
			# TODO: Check whether things break when a solver is removed which still has instances left in the job list
			if status == 'WRONG':
				remove_faulty_solver(solver_path, instance_path)
				current_job_num += 1

				continue # Skip to the next job

			# Update performance CSV
			if performance_measure == PerformanceMeasure.QUALITY_ABSOLUTE:
				# TODO: Handle the multi-objective case for quality
				performance_data_csv.set_value(instance_path, solver_path, quality[0])
				print('c Running Result: Status: ' + status + ', Quality' + penalised_str + ': ' + str(quality[0]))
			else:
				performance_data_csv.set_value(instance_path, solver_path, runtime)
				print('c Running Result: Status ' + status + ', Runtime' + penalised_str + ': ' + str(runtime))

			print(r'c Executing Progress: ' + str(current_job_num) + ' out of ' + str(total_job_num))
			current_job_num += 1

	performance_data_csv.update_csv()
	sfh.write_string_to_file(sgh.cutoff_time_information_txt_path, "cutoff_time_each_run = " + cutoff_time_str)
	sfh.append_string_to_file(sgh.cutoff_time_information_txt_path, "par_num = " + str(sgh.settings.get_general_penalty_multiplier()))
	print('c Performance data file ' + performance_data_csv_path + ' has been updated!')
	
	return


def handle_timeouts(runtime, status):
	if runtime > sgh.settings.get_general_target_cutoff_time():
		status = 'TIMEOUT' # Overwrites possible user status...
	if status == 'TIMEOUT' or status == 'UNKNOWN':
		runtime = sgh.settings.get_penalised_time()

	return runtime, status


def verify(instance_path, raw_result_path, solver_path, status):
	verifier = sgh.settings.get_general_solution_verifier()

	# Use verifier if one is given and the solver did not time out
	if verifier == SolutionVerifier.SAT and status != 'TIMEOUT' and status != 'UNKNOWN':
		status = sat_verify(instance_path, raw_result_path, solver_path)

	return status


def process_results(raw_result_path, solver_wrapper_path, runsolver_values_path):
	# By default runtime comes from runsolver, may be overwritten by user wrapper
	runtime = get_runtime_from_runsolver(runsolver_values_path)

	# Get results from the wrapper
	cmd_get_results_from_wrapper = solver_wrapper_path + ' --print-output ' + raw_result_path
	results = os.popen(cmd_get_results_from_wrapper)
	result_lines = results.readlines()

	if len(result_lines) <= 0:
		# TODO: Add instructions for the user that might fix the issue?
		print('c ERROR: Failed to get output from wrapper at \'' + solver_wrapper_path + '\' stopping execution!')
		sys.exit()

	# Check if Sparkle should use it's own parser
	first_line = result_lines[0]
	first_line_parts = first_line.strip().split()

	if len(first_line_parts) == 4 and first_line_parts[0].lower() == 'use' and first_line_parts[1].lower() == 'sparkle':
		if first_line_parts[2].lower() == 'sat':
			quality = [] # Not defined for SAT
			status = sparkle_sat_parser(raw_result_path, runtime)
		else:
			parser_list = 'SAT'
			print('c ERROR: Wrapper at \'' + solver_wrapper_path + '\' requested Sparkle to use an internal parser that does not exist\nc Possible internal parsers: ' + parser_list + '\nc If your problem domain is not in the list, please parse the output in the wrapper.\nc Stopping execution!')
			sys.exit()
	else:
		# Read output
		quality = []
		status = 'UNKNOWN'
		for line in result_lines:
			parts = line.strip().split()
			# Skip empty lines
			if len(parts) <= 0:
				continue
			# Handle lines that are too short
			if len(parts) <= 1:
				print('c Warning: The line \'' + line.strip() + '\' contains no result information or is not formatted correctly: <quality/status/runtime> VALUE')
			if parts[0].lower() == 'quality':
				quality = get_quality_from_wrapper(parts)
			elif parts[0].lower() == 'status':
				status = get_status_from_wrapper(parts)
			elif parts[0].lower() == 'runtime':
				runtime = get_runtime_from_wrapper(parts)
			# TODO: Handle unknown keywords?

	return runtime, quality, status


# quality -- comma separated list of quality measurements; [required when one or more quality objectives are used, optional otherwise]
# In: List of words
# Out: List of floats
def get_quality_from_wrapper(result_list):
	quality = []

	for i in range(1, len(result_list)):
		quality.append(float(result_list[i]))
	
	return quality


# status [optional, SUCCESS assumed]
# In: List of words
# Out: String
def get_status_from_wrapper(result_list):
	status_list = '<SUCCESS/TIMEOUT/CRASHED/SAT/UNSAT/WRONG/UNKNOWN>'
	status = 'SUCCESS'

	if result_list[1].upper() == 'SUCCESS':
		status = 'SUCCESS'
	elif result_list[1].upper() == 'TIMEOUT':
		status = 'TIMEOUT'
	elif result_list[1].upper() == 'CRASHED':
		status = 'CRASHED'
	elif result_list[1].upper() == 'SAT':
		status = 'SAT'
	elif result_list[1].upper() == 'UNSAT':
		status = 'UNSAT'
	elif result_list[1].upper() == 'WRONG':
		status = 'WRONG'
	elif result_list[1].upper() == 'UNKNOWN':
		status = 'UNKNOWN'
	else:
		print('c ERROR: Invalid status \'' + result_list[1] + '\' given, possible statuses are: ' + status_list + '\nc Stopping execution!')
		sys.exit()

	return status


# runtime -- in seconds, will overwrite Sparkle's own measurement (through runsolver) if given [optional]
# In: List of words
# Out: Float
def get_runtime_from_wrapper(result_list):

	runtime = float(result_list[1])

	return runtime


# Read runtime as CPU time from runsolver values file '-v'
# In: Path to runsolver values file
# Out: Float
def get_runtime_from_runsolver(runsolver_values_path) -> float:
	runtime = float(-1)

	infile = open(runsolver_values_path, 'r+')
	fcntl.flock(infile.fileno(), fcntl.LOCK_EX)

	while True:
		line = infile.readline().strip()
		if not line:
			break
		# Read runtime from a line of the form 'CPUTIME=0.110449'
		words = line.split('=')
		if len(words) == 2 and words[0] == 'CPUTIME':
			runtime = float(words[1])
			break

	infile.close()

	return runtime


# In: Path to raw result, runtime
# Out: Status string
def sparkle_sat_parser(raw_result_path, runtime):
	if runtime > sgh.settings.get_general_target_cutoff_time():
		status = 'TIMEOUT'
	else: 
		status = sat_get_result(raw_result_path)

	return status


# In: Path to solver, path to instance it failed on
# Out: N/A
def remove_faulty_solver(solver_path, instance_path):
	wrong_solver_list.append(solver_path)
	print(r'c Warning: Solver ' + sfh.get_last_level_directory_name(solver_path) + r' reports the wrong answer on instance ' + sfh.get_last_level_directory_name(instance_path) + r'!')
	print(r'c Warning: Solver ' + sfh.get_last_level_directory_name(solver_path) + r' will be removed!')

	performance_data_csv.delete_column(solver_path)
	sgh.solver_list.remove(solver_path)
	sgh.solver_nickname_mapping.pop(solver_path)
	sfh.write_solver_list()
	sfh.write_solver_nickname_mapping()

	print(r'c Solver ' + sfh.get_last_level_directory_name(solver_path) + r' is a wrong solver')
	print(r'c Solver ' + sfh.get_last_level_directory_name(solver_path) + ' running on instance ' + sfh.get_last_level_directory_name(instance_path) + ' ignored!')
	print(r'c')

	return


# In: Paths to instance, result, and solver
# Out: Status string
def sat_verify(instance_path, raw_result_path, solver_path):
	verify_string = sat_judge_correctness_raw_result(instance_path, raw_result_path)

	runtime = -1
	status = 'UNKNOWN'

	if verify_string == 'SAT':
		status = 'SAT'
		if sgh.instance_reference_mapping[instance_path] != r'SAT':
			sgh.instance_reference_mapping[instance_path] = r'SAT'
			sfh.write_instance_reference_mapping()
	elif verify_string == 'UNSAT':
		status = 'UNSAT'
		if sgh.instance_reference_mapping[instance_path] != r'UNSAT':
			sgh.instance_reference_mapping[instance_path] = r'UNSAT'
			sfh.write_instance_reference_mapping()
	elif verify_string == 'WRONG':
		status = 'WRONG'
	else:
		status = 'UNKNOWN'
		print('c Warning: Verification result was UNKNOWN for solver ' + sfh.get_last_level_directory_name(solver_path) + ' on instance ' + sfh.get_last_level_directory_name(instance_path) + '!')

	# TODO: Make removal conditional on a success status (SAT or UNSAT)
	#command_line = r'rm -f ' + raw_result_path
	#os.system(command_line)

	return status


def sat_get_result(raw_result_path):
	# If no result is reported in the result file something went wrong or the solver timed out
	result = 'UNKNOWN'

	infile = open(raw_result_path, 'r+')
	fcntl.flock(infile.fileno(), fcntl.LOCK_EX)

	while True:
		line = infile.readline().strip()
		if not line:
			break
		words = line.split()
		if len(words) == 3 and words[1] == 's':
			if words[2] == 'SATISFIABLE':
				result = 'SAT'
			elif words[2] == 'UNSATISFIABLE':
				result = 'UNSAT'
			else:
				# Something is wrong or the solver timed out
				print('c Warning: Unknown SAT result \'' + words[2] + '\'')
				result = 'UNKNOWN'
			break

	infile.close()

	return result


def sat_get_verify_string(tmp_verify_result_path):
	#4 return values: 'SAT', 'UNSAT', 'WRONG', 'UNKNOWN'
	ret = 'UNKNOWN'
	fin = open(tmp_verify_result_path, 'r+')
	fcntl.flock(fin.fileno(), fcntl.LOCK_EX)
	while True:
		myline = fin.readline()
		myline = myline.strip()
		if not myline: break
		if myline == r'Solution verified.':
			myline2 = fin.readline()
			myline2 = fin.readline().strip()
			if myline2 == r'11':
				ret = r'SAT'
				break
		elif myline == r'Solver reported unsatisfiable. I guess it must be right!':
			myline2 = fin.readline()
			myline2 = fin.readline().strip()
			if myline2 == r'10':
				ret = r'UNSAT'
				break
		elif myline == r'Wrong solution.':
			myline2 = fin.readline()
			myline2 = fin.readline().strip()
			if myline2 == r'0':
				ret = 'WRONG'
				break
		else:
			continue	
	fin.close()
	return ret


def sat_judge_correctness_raw_result(instance_path, raw_result_path):
	SAT_verifier_path = sgh.SAT_verifier_path
	tmp_verify_result_path = r'Tmp/'+ sfh.get_last_level_directory_name(SAT_verifier_path) + r'_' + sfh.get_last_level_directory_name(raw_result_path) + r'_' + sbh.get_time_pid_random_string() + r'.vryres'
	# TODO: Log output file
	command_line = SAT_verifier_path + r' ' + instance_path + r' ' + raw_result_path + r' > ' + tmp_verify_result_path
	print('c Run SAT verifier')
	os.system(command_line)
	print('c SAT verifier done')

	ret = sat_get_verify_string(tmp_verify_result_path)

	# TODO: Log output file removal
	command_line = 'rm -f ' + tmp_verify_result_path
	os.system(command_line)
	return ret

