#!/usr/bin/env python2.7
# -*- coding: UTF-8 -*-

'''
Software: 	Sparkle (Platform for evaluating empirical algorithms/solvers)

Authors: 	Chuan Luo, chuanluosaber@gmail.com
			Holger H. Hoos, hh@liacs.nl

Contact: 	Chuan Luo, chuanluosaber@gmail.com
'''

import os
import sys
import fcntl
import sparkle_basic_help
import sparkle_record_help
import sparkle_file_help as sfh
import sparkle_global_help
import sparkle_feature_data_csv_help as sfdcsv
import sparkle_performance_data_csv_help as spdcsv
import sparkle_run_solvers_help as srs

def generate_constructing_portfolio_selector_shell_script(sbatch_shell_script_path, num_job_in_parallel, performance_data_csv_path_train, performance_data_csv_path_validate, feature_data_csv_path_train, feature_data_csv_path_validate, cutoff_time_each_run, par_num, list_jobs, start_index, end_index):
	job_name = sfh.get_file_name(sbatch_shell_script_path)
	num_job_total = end_index - start_index
	if num_job_in_parallel > num_job_total:
		num_job_in_parallel = num_job_total
	command_prefix = r'srun -N1 -n1 --exclusive python2 Commands/sparkle_help/construct_portfolio_selector_one_time_core.py '
	
	fout = open(sbatch_shell_script_path, 'w+')
	fcntl.flock(fout.fileno(), fcntl.LOCK_EX)
	
	fout.write(r'#!/bin/bash' + '\n')
	fout.write(r'###' + '\n')
	fout.write(r'#SBATCH --job-name=' + job_name + '\n')
	fout.write(r'#SBATCH --output=' + r'TMP/tmp/%A_%a.txt' + '\n')
	fout.write(r'#SBATCH --error=' + r'TMP/tmp/%A_%a.err' + '\n')
	fout.write(r'###' + '\n')
	fout.write(r'###' + '\n')
	fout.write(r'#SBATCH --partition=grace30' + '\n')
	fout.write('#SBATCH --mem-per-cpu=3000' + '\n')
	fout.write(r'#SBATCH --array=0-' + str(num_job_total-1) + r'%' + str(num_job_in_parallel) + '\n')
	fout.write(r'###' + '\n')
	
	fout.write('params=( \\' + '\n')
	
	for i in range(start_index, end_index):
		portfolio_selector_path = list_jobs[i][0]
		excluded_solver = list_jobs[i][1]
		run_id_int = list_jobs[i][2]
		fout.write('\'%s %s %s %s %s %d %d %d %s\'\n' % (portfolio_selector_path, performance_data_csv_path_train, performance_data_csv_path_validate, feature_data_csv_path_train, feature_data_csv_path_validate, cutoff_time_each_run, par_num, run_id_int, excluded_solver))
	
	fout.write(r')' + '\n')

	command_line = command_prefix + r' ' + r'${params[$SLURM_ARRAY_TASK_ID]}'
	
	fout.write(command_line + '\n')
	
	fout.close()
	return

def constructing_portfolio_selector_parallel(portfolio_selector_path_basis, num_job_in_parallel, performance_data_csv_path_train, performance_data_csv_path_validate, feature_data_csv_path_train, feature_data_csv_path_validate, cutoff_time_each_run, par_num, round_count=5):
	performance_data_csv_train = spdcsv.Sparkle_Performance_Data_CSV(performance_data_csv_path_train)
	
	total_job_list = []
	
	portfolio_selector_path = portfolio_selector_path_basis
	excluded_solver = ''
	for i in range(0, round_count):
		total_job_list.append([portfolio_selector_path, excluded_solver, i])
	
	for excluded_solver in performance_data_csv_train.list_columns():
		portfolio_selector_path = portfolio_selector_path_basis
		for i in range(0, round_count):
			total_job_list.append([portfolio_selector_path, excluded_solver, i])
	
	i = 0
	j = len(total_job_list)
	sbatch_shell_script_path = 'TMP/' + r'constructing_portfolio_selector_sbatch_shell_script_' + str(i) + '_' + str(j) + '_' + sparkle_basic_help.get_time_pid_random_string() + r'.sh'
	generate_constructing_portfolio_selector_shell_script(sbatch_shell_script_path, num_job_in_parallel, performance_data_csv_path_train, performance_data_csv_path_validate, feature_data_csv_path_train, feature_data_csv_path_validate, cutoff_time_each_run, par_num, total_job_list, i, j)

	os.system(r'chmod a+x ' + sbatch_shell_script_path)
	command_line = r'sbatch ' + sbatch_shell_script_path
	
	#os.system(command_line)
	output_list = os.popen(command_line).readlines()
	if len(output_list) > 0 and len(output_list[0].strip().split())>0:
		run_solvers_parallel_jobid = output_list[0].strip().split()[-1]
	else:
		run_solvers_parallel_jobid = ''
	return run_solvers_parallel_jobid

