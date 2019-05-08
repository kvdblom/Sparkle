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
from sparkle_help import sparkle_global_help
from sparkle_help import sparkle_basic_help
from sparkle_help import sparkle_record_help
from sparkle_help import sparkle_file_help as sfh
from sparkle_help import sparkle_feature_data_csv_help as sfdcsv
from sparkle_help import sparkle_performance_data_csv_help as spdcsv
from sparkle_help import sparkle_compute_features_help as scf
from sparkle_help import sparkle_run_solvers_help as srs
from sparkle_help import sparkle_compute_features_parallel_help as scfp
from sparkle_help import sparkle_run_solvers_parallel_help as srsp
from sparkle_help import sparkle_csv_merge_help
from sparkle_help import sparkle_experiments_related_help

if __name__ == r'__main__':


	my_flag_run_extractor_later = False
	my_flag_run_solver_later = False
	my_flag_nickname = False
	my_flag_parallel = False
	my_flag_all_unsat = False
	nickname_str = r''
	instances_source = r''

	len_argv = len(sys.argv)
	i = 1
	while i<len_argv:
		if sys.argv[i] == r'-run-extractor-later':
			my_flag_run_extractor_later = True
		elif sys.argv[i] == r'-run-solver-later':
			my_flag_run_solver_later = True
		elif sys.argv[i] == r'-nickname':
			my_flag_nickname = True
			i += 1
			nickname_str = sys.argv[i]
		elif sys.argv[i] == r'-parallel':
			my_flag_parallel = True
		elif sys.argv[i] == r'-all-unsat':
			my_flag_all_unsat = True
		else:
			instances_source = sys.argv[i]
			if instances_source[-1]!= '/':
				instances_source += '/'
		i += 1

	if not os.path.exists(instances_source):
		print r'c Instances path ' + "\'" + instances_source + "\'" + r' does not exist!'
		print r'c Usage: ' + sys.argv[0] + r' [-run-extractor-later] [-run-solver-later] [-nickname] [<nickname>] [-all-unsat] [-parallel] <instances_source_directory>'
		sys.exit()

	print 'c Start adding all cnf instances in directory ' + instances_source + r' ...' 

	last_level_directory = r''
	if my_flag_nickname: last_level_directory = nickname_str
	else: last_level_directory = sfh.get_last_level_directory_name(instances_source)

	if last_level_directory[-1] != '/':
		last_level_directory += '/'

	instances_diretory = r'Instances/' + last_level_directory
	if not os.path.exists(instances_diretory): os.mkdir(instances_diretory)

	#os.system(r'cp ' + instances_source + r'/*.cnf ' + instances_diretory)
	list_source_all_cnf_filename = sfh.get_list_all_cnf_filename(instances_source)
	list_target_all_cnf_filename = sfh.get_list_all_cnf_filename(instances_diretory)

	feature_data_csv = sfdcsv.Sparkle_Feature_Data_CSV(sparkle_global_help.feature_data_csv_path)
	performance_data_csv = spdcsv.Sparkle_Performance_Data_CSV(sparkle_global_help.performance_data_csv_path)

	num_cnf = len(list_source_all_cnf_filename)
	
	print 'c The number of intended adding instances: ' + str(num_cnf)

	for i in range(0, len(list_source_all_cnf_filename)):
		source_cnf_path = list_source_all_cnf_filename[i]
		print r'c'
		print r'c Adding ' + source_cnf_path + r' ...'
		print 'c Executing Progress: ' + str(i+1) + ' out of ' + str(num_cnf)
		
		if 'Instances/' + source_cnf_path in list_target_all_cnf_filename:
			print r'c Instance ' + sfh.get_last_level_directory_name(source_cnf_path) + r' already exists in Directory ' + instances_diretory
			print r'c Ignore adding file ' + sfh.get_last_level_directory_name(source_cnf_path)
			#continue
		else:
			target_cnf_path = source_cnf_path.replace(instances_source, instances_diretory)
			if my_flag_all_unsat:
				target_cnf_status = 'UNSAT'
			else:
				target_cnf_status = 'UNKNOWN'
			sparkle_global_help.instance_list.append(target_cnf_path)
			sparkle_global_help.instance_reference_mapping[target_cnf_path] = target_cnf_status
			sfh.add_new_instance_into_file(target_cnf_path)
			sfh.add_new_instance_reference_into_file(target_cnf_path, target_cnf_status)
			feature_data_csv.add_row(target_cnf_path)
			performance_data_csv.add_row(target_cnf_path)
			
			if not os.path.exists(sfh.get_all_level_directory(target_cnf_path)):
				os.system('mkdir -p ' + sfh.get_all_level_directory(target_cnf_path))
			command = 'cp ' + source_cnf_path + ' ' + target_cnf_path
			os.system(command)
			
			print r'c Instance ' + sfh.get_last_level_directory_name(source_cnf_path) + r' has been added!'
			print r'c'

	feature_data_csv.update_csv()
	performance_data_csv.update_csv()
	
	print 'c Adding instances ' + sfh.get_last_level_directory_name(instances_diretory) + ' done!'

	if os.path.exists(sparkle_global_help.sparkle_portfolio_selector_path):
		command_line = r'rm -f ' + sparkle_global_help.sparkle_portfolio_selector_path
		os.system(command_line)
		command_line = r'rm -f ' + sparkle_global_help.sparkle_portfolio_selector_path + '*'
		os.system(command_line)
		print 'c Removing Sparkle portfolio selector ' + sparkle_global_help.sparkle_portfolio_selector_path + ' done!'
	
	if os.path.exists(sparkle_global_help.sparkle_report_path):
		command_line = r'rm -f ' + sparkle_global_help.sparkle_report_path
		os.system(command_line)
		print 'c Removing Sparkle report ' + sparkle_global_help.sparkle_report_path + ' done!'
	
	if not my_flag_run_extractor_later:
		if not my_flag_parallel:
			print 'c Start computing features ...'
			scf.computing_features(sparkle_global_help.feature_data_csv_path, 1)
			print 'c Feature data file ' + sparkle_global_help.feature_data_csv_path + ' has been updated!'
			print 'c Computing features done!'
		else:
			num_job_in_parallel = sparkle_experiments_related_help.num_job_in_parallel
			scfp.computing_features_parallel(sparkle_global_help.feature_data_csv_path, num_job_in_parallel, 1)
			print 'c Computing features in parallel ...'

	if not my_flag_run_solver_later:
		if not my_flag_parallel:
			print 'c Start running solvers ...'
			srs.running_solvers(sparkle_global_help.performance_data_csv_path, 1)
			print 'c Performance data file ' + sparkle_global_help.performance_data_csv_path + ' has been updated!'
			print 'c Running solvers done!'
		else:
			num_job_in_parallel = sparkle_experiments_related_help.num_job_in_parallel
			srsp.running_solvers_parallel(sparkle_global_help.performance_data_csv_path, num_job_in_parallel, 1)
			print 'c Running solvers in parallel ...'
			

