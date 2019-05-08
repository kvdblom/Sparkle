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

curDir = os.path.abspath(__file__)
curDir = curDir[:curDir.rfind('/')]
sys.path.append(os.path.join(curDir, 'sparkle_help/'))
sys.path.append(os.path.join(curDir, 'sparkle_test_help/'))

from sparkle_csv_help import Sparkle_CSV
from sparkle_feature_data_csv_help import Sparkle_Feature_Data_CSV
from sparkle_performance_data_csv_help import Sparkle_Performance_Data_CSV

from sparkle_portfolio_test_help import Portfolio_Test
import sparkle_experiments_related_help

if __name__ == r'__main__':

	len_argv = len(sys.argv)
	if len_argv != 2:
		print('c Arguments Error!')
		print('c Usage: %s <test_instance_dir>' % (sys.argv[0]))
		sys.exit(-1)

	test_instance_dir = sys.argv[1]

	portfolio_test = Portfolio_Test(test_instance_dir)
	jobid_1 = portfolio_test.computing_features_parallel()
	jobid_2 = portfolio_test.running_solvers_parallel()
	portfolio_test.analysing_portfolio_parallel([jobid_1, jobid_2])
	#portfolio_test.generating_report()

