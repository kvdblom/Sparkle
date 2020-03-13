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
from sparkle_help import sparkle_file_help as sfh

def check_adding_solver_contain_pcs_file(solver_diretory):
	list_files = os.listdir(solver_diretory)
	for file_name in list_files:
		file_extension = sfh.get_file_least_extension(file_name)
		if file_extension == 'pcs':
			return True
	return False

def get_pcs_file_from_solver_directory(solver_diretory):
	list_files = os.listdir(solver_diretory)
	for file_name in list_files:
		file_extension = sfh.get_file_full_extension(file_name)
		if file_extension == 'pcs':
			return file_name
	return r''






	
