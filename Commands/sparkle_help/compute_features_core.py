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

try:
	from sparkle_help import sparkle_global_help
	from sparkle_help import sparkle_basic_help
	from sparkle_help import sparkle_file_help as sfh
	from sparkle_help import sparkle_feature_data_csv_help as sfdcsv
	from sparkle_help import sparkle_experiments_related_help as ser
	from sparkle_help import sparkle_job_help
	from sparkle_help import sparkle_compute_features_help as scf
except ImportError:
	import sparkle_global_help
	import sparkle_basic_help
	import sparkle_file_help as sfh
	import sparkle_feature_data_csv_help as sfdcsv
	import sparkle_experiments_related_help as ser
	import sparkle_job_help
	import sparkle_compute_features_help as scf

if __name__ == r'__main__':
	instance_path = sys.argv[1]
	extractor_path = sys.argv[2]
	feature_data_csv_path = sys.argv[3]
	
	feature_data_csv = sfdcsv.Sparkle_Feature_Data_CSV(feature_data_csv_path)
	
	runsolver_path = sparkle_global_help.runsolver_path
	if len(sparkle_global_help.extractor_list)==0: cutoff_time_each_extractor_run = ser.cutoff_time_total_extractor_run_on_one_instance + 1
	else: cutoff_time_each_extractor_run = ser.cutoff_time_total_extractor_run_on_one_instance/len(sparkle_global_help.extractor_list) + 1
	cutoff_time_each_run_option = r'-C ' + str(cutoff_time_each_extractor_run)
	
	key_str = sfh.get_last_level_directory_name(extractor_path) + r'_' + sfh.get_last_level_directory_name(instance_path) + r'_' + sparkle_basic_help.get_time_pid_random_string()
	result_path = r'Feature_Data/TMP/' + key_str + r'.csv'
	basic_part = r'TMP/' + key_str
	#result_path = basic_part + r'.rawres'
	err_path = basic_part + r'.err'
	runsolver_watch_data_path = basic_part + r'.log'
	runsolver_watch_data_path_option = r'-w ' + runsolver_watch_data_path
	command_line = runsolver_path + r' ' + cutoff_time_each_run_option + r' ' + runsolver_watch_data_path_option + r' ' + extractor_path + r'/' + sparkle_global_help.sparkle_run_default_wrapper + r' ' + extractor_path + r'/' + r' ' + instance_path + r' ' + result_path + r' 2> ' + err_path

	try:
		task_run_status_path = r'TMP/SBATCH_Extractor_Jobs/' + key_str + r'.statusinfo'
		status_info_str = 'Status: Running\n' + 'Extractor: %s\n' %(sfh.get_last_level_directory_name(extractor_path)) + 'Instance: %s\n' % (sfh.get_last_level_directory_name(instance_path))
		
		start_time = time.time()
		status_info_str += 'Start Time: ' + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(start_time)) + '\n'
		status_info_str += 'Start Timestamp: ' + str(start_time) + '\n'
		cutoff_str = 'Cutoff Time: ' + str(cutoff_time_each_extractor_run) + ' second(s)' + '\n'
		status_info_str += cutoff_str
		sfh.write_string_to_file(task_run_status_path, status_info_str)
		os.system(command_line)
		end_time = time.time()
		
	except:
		if not os.path.exists(result_path):
			sfh.create_new_empty_file(result_path)
	
	try:
		tmp_fdcsv = sfdcsv.Sparkle_Feature_Data_CSV(result_path)
		result_string = 'Successful'
	except:
		print('c ****** WARNING: Feature vector computing on instance ' + instance_path + ' failed! ******')
		print('c ****** WARNING: The feature vector of this instace consists of missing values ******')
		command_line = r'rm -f ' + result_path
		os.system(command_line)
		tmp_fdcsv = scf.generate_missing_value_csv_like_feature_data_csv(feature_data_csv, instance_path, extractor_path, result_path)
		result_string = 'Failed -- using missing value instead'
		
	description_str = r'[Extractor: ' + sfh.get_last_level_directory_name(extractor_path) + r', Instance: ' + sfh.get_last_level_directory_name(instance_path) + r']'
	start_time_str = r'[Start Time: ' + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(start_time)) + r']'
	end_time_str = r'[End Time: ' + time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(end_time)) + r']'
	run_time_str = r'[Actual Run Time: ' + str(end_time-start_time) + r' second(s)]'
	result_string_str = r'[Result String: ' + result_string + r']'
	
	log_str = description_str + r', ' + start_time_str + r', ' + end_time_str + r', ' + run_time_str + r', ' + result_string_str
	
	time.sleep(random.randint(1, 5))
	
	sfh.append_string_to_file(sparkle_global_help.sparkle_system_log_path, log_str)
	os.system('rm -f ' + task_run_status_path)
	
	#feature_data_csv.combine(tmp_fdcsv)
	#feature_data_csv.update_csv()
	feature_data_csv.reload_and_combine_and_update(tmp_fdcsv)
	
	#tmp_fdcsv.update_csv()
	
	command_line = r'rm -f ' + result_path
	os.system(command_line)
	command_line = r'rm -f ' + err_path
	os.system(command_line)
	command_line = r'rm -f ' + runsolver_watch_data_path
	os.system(command_line)

