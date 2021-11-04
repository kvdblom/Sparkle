#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
from pathlib import PurePath
from pathlib import Path

from sparkle_help import sparkle_global_help as sgh
from sparkle_help import sparkle_file_help as sfh
from sparkle_help import sparkle_logging as sl
from sparkle_help import sparkle_generate_report_help as sgrh
from sparkle_help.sparkle_settings import PerformanceMeasure


def get_numSolvers(parallel_portfolio_path: Path):
    solver_list = sfh.get_solver_list_from_parallel_portfolio(parallel_portfolio_path)
    num_solvers = len(solver_list)
    # If a solver contains multiple solver_variations.
    for solver in solver_list:
        if ' ' in solver:
            num_solvers += int(solver[solver.rfind(' ')+1:]) - 1

    str_value = str(num_solvers)

    if int(str_value) < 1:
        print('ERROR: No solvers found, report generation failed!')
        sys.exit()

    return str_value


def get_solverList(parallel_portfolio_path: Path):
    str_value = ''
    solver_list = sfh.get_solver_list_from_parallel_portfolio(parallel_portfolio_path)

    for solver_path in solver_list:
        solver_variations = 0

        if ' ' in solver_path:
            solver_variations = int(solver_path[solver_path.rfind(' ')+1:])
            solver_path = solver_path[:solver_path.rfind(' ')]

        solver_name = sfh.get_file_name(solver_path)

        if solver_name == '':
            solver_name = sfh.get_last_level_directory_name(solver_path)

        x = solver_name.rfind('_')

        if str(x) != '-1':
            solver_name = solver_name[:x] + '\\' + solver_name[x:]

        str_value += r'\item \textbf{' + f'{sgrh.underscore_for_latex(solver_name)}}}\n'

        if solver_variations > 1:
            seed_number = ''

            for instances in range(1, solver_variations+1):
                seed_number += str(instances)

                if instances != solver_variations:
                    seed_number += ','

            str_value += r'\item[] With seeds: ' + seed_number + '\n'

    return str_value


def get_num_instance_classes(instance_list: list[str]) -> str:
    list_instance_class = []

    for instance_path in instance_list:
        instance_class = sfh.get_current_directory_name(instance_path)

    if not (instance_class in list_instance_class):
        list_instance_class.append(instance_class)

    str_value = str(len(list_instance_class))

    if int(str_value) < 1:
        print('ERROR: No instance sets found, report generation failed!')
        sys.exit()

    return str_value


def get_instanceClassList(instance_list: list[str]) -> (str, int):
    str_value = ''
    nr_of_instances = 0
    list_instance_class = []
    dict_n_instances_in_class = {}

    for instance_path in instance_list:
        instance_class = sfh.get_current_directory_name(instance_path)

        if not (instance_class in list_instance_class):
            list_instance_class.append(instance_class)
            dict_n_instances_in_class[instance_class] = 1
        else:
            dict_n_instances_in_class[instance_class] += 1

    for instance_class in list_instance_class:
        str_value += (r'\item \textbf{' + sgrh.underscore_for_latex(instance_class)
                      + '}, number of instances: '
                      + str(dict_n_instances_in_class[instance_class]) + '\n')
        nr_of_instances += int(dict_n_instances_in_class[instance_class])

    return str_value, nr_of_instances


def get_results() -> dict[str, list[str, str]]:
    """Returns a dict with the performance results on each instance.

    The dict consists of a string indicating the instance name, and a list which contains
    the solver name followed by the performance.
    """
    solutions_dir = sgh.pap_performance_data_tmp_path
    results = sfh.get_list_all_result_filename(str(solutions_dir))
    results_dict = dict()

    for result in results:
        result_path = Path(solutions_dir / result)

        with open(result_path, 'r') as result_file:
            lines = result_file.readlines()

        result_lines = [line.strip() for line in lines]

        if len(result_lines) == 3:
            instance = Path(result_lines[0]).name

            if instance in results_dict:
                if float(results_dict[instance][1]) > float(result_lines[2]):
                    results_dict[instance][0] = result_lines[1]
                    results_dict[instance][1] = result_lines[2]
            else:
                results_dict[instance] = [result_lines[1], result_lines[2]]

    return results_dict


def get_solversWithSolution() -> (str, dict[str, int], int):
    results_on_instances = get_results()
    str_value = ''

    if sgh.settings.get_general_performance_measure() == PerformanceMeasure.RUNTIME:
        solver_dict = dict()
        unsolved_instances = 0

        for instances in results_on_instances:
            solver_name = sfh.get_file_name(results_on_instances[instances][0])
            cutoff_time = str(sgh.settings.get_penalised_time())

            if results_on_instances[instances][1] != cutoff_time:
                if '_seed_' in solver_name:
                    solver_name = solver_name[:solver_name.rfind('_seed_')+7]
                if solver_name in solver_dict:
                    solver_dict[solver_name] = solver_dict[solver_name] + 1
                else:
                    solver_dict[solver_name] = 1
            else:
                unsolved_instances += 1

    if(sgh.settings.get_general_performance_measure()
            == PerformanceMeasure.QUALITY_ABSOLUTE):
        # TODO: Assign values to solver_dict and unsolved_instances ?!
        for instances in results_on_instances:
            str_value += (r'\item \textbf{' + sgrh.underscore_for_latex(instances)
                          + '}, was scored by: ' + r'\textbf{'
                          + sgrh.underscore_for_latex(sfh.get_last_level_directory_name(
                              results_on_instances[instances][0]))
                          + '} with a score of '
                          + str(results_on_instances[instances][1]))
    else:
        for solver in solver_dict:
            str_value += (r'\item Solver \textbf{' + sgrh.underscore_for_latex(solver)
                          + '}, was the best solver on ' + r'\textbf{'
                          + str(solver_dict[solver]) + '} instance(s)')
        if unsolved_instances:
            str_value += (r'\item \textbf{' + str(unsolved_instances)
                          + '} instance(s) remained unsolved')

    return str_value, solver_dict, unsolved_instances


def get_dict_sbs_penalty_time_on_each_instance(
        parallel_portfolio_path: Path,
        instance_list: list[str]) -> (dict[str, float], str, dict[str, float]):
    """Return the penalised run time for the single best solver and per solver.

    The first returned dict contains the run time per instance for the single best
    solver, the returned string contains the name of the single best solver, and the
    second returned dict contains penalised average run time per solver.
    """
    # Collect full solver list, including solver variants
    solver_list = sfh.get_solver_list_from_parallel_portfolio(parallel_portfolio_path)
    full_solver_list = []

    for lines in solver_list:
        if ' ' in lines:
            for solver_variations in range(1, int(lines[lines.rfind(' ')+1:])+1):
                solver_path = Path(lines[:lines.rfind(' ')])
                solver_variant_name = solver_path.name

                if '/' in solver_variant_name:
                    solver_variant_name = (
                        solver_variant_name[:solver_variant_name.rfind('/')])

                solver_variant_name = (
                    f'{sgh.sparkle_tmp_path}{solver_variant_name}_seed_'
                    f'{str(solver_variations)}')
                full_solver_list.append(solver_variant_name)
        else:
            full_solver_list.append(lines)

    # Collect penalised average run time (PAR) results for all solvers
    all_solvers_dict = {}
    results = get_results()

    for instance in instance_list:
        instance_name = Path(instance).name
        penalised_time = float(sgh.settings.get_penalised_time())

        if instance_name in results:
            run_time = float(results[instance_name][1])

            if run_time <= sgh.settings.get_general_target_cutoff_time():
                for solver in full_solver_list:
                    # in because the solver name contains the instance name as well,
                    # or the solver can have an additional '/' at the end of the path
                    if(solver in results[instance_name][0]
                            or results[instance_name][0] in solver):
                        if solver in all_solvers_dict:
                            all_solvers_dict[solver] += run_time
                        else:
                            all_solvers_dict[solver] = run_time
                    else:
                        if solver in all_solvers_dict:
                            all_solvers_dict[solver] += penalised_time
                        else:
                            all_solvers_dict[solver] = penalised_time
            else:
                for solver in full_solver_list:
                    if solver in all_solvers_dict:
                        all_solvers_dict[solver] += penalised_time
                    else:
                        all_solvers_dict[solver] = penalised_time
        else:
            for solver in full_solver_list:
                if solver in all_solvers_dict:
                    all_solvers_dict[solver] += penalised_time
                else:
                    all_solvers_dict[solver] = penalised_time

    # Find the single best solver (SBS)
    sbs_name = min(all_solvers_dict, key=all_solvers_dict.get)
    sbs_name = Path(sbs_name).name
    sbs_dict = {}

    for instance in instance_list:
        instance_name = sfh.get_last_level_directory_name(instance)

        if sbs_name in results[instance_name][0]:
            sbs_dict[instance_name] = results[instance_name][1]
        else:
            sbs_dict[instance_name] = sgh.settings.get_penalised_time()

    return sbs_dict, sbs_name, all_solvers_dict


def get_dict_actual_parallel_portfolio_penalty_time_on_each_instance(
        instance_list: list[str]) -> dict[str, float]:
    mydict = {}

    cutoff_time = sgh.settings.get_general_target_cutoff_time()
    results = get_results()

    for instance in instance_list:
        instance_name = sfh.get_last_level_directory_name(instance)

        if instance_name in results:
            if float(results[instance_name][1]) <= cutoff_time:
                mydict[instance_name] = float(results[instance_name][1])
            else:
                mydict[instance_name] = float(sgh.settings.get_penalised_time())
        else:
            mydict[instance_name] = float(sgh.settings.get_penalised_time())

    return mydict


def get_figure_parallel_portfolio_sparkle_vs_sbs(parallel_portfolio_path: Path,
                                                 instances: list[str]):
    str_value = ''
    dict_sbs_penalty_time_on_each_instance, sbs_solver, dict_all_solvers = (
        get_dict_sbs_penalty_time_on_each_instance(parallel_portfolio_path, instances))
    dict_actual_parallel_portfolio_penalty_time_on_each_instance = (
        get_dict_actual_parallel_portfolio_penalty_time_on_each_instance(instances))

    latex_directory_path = 'Components/Sparkle-latex-generator-for-parallel-portfolio/'
    figure_filename = (
        'figure_parallel_portfolio_sparkle_vs_sbs')
    data_filename = (
        'data_parallel_portfolio_sparkle_vs_sbs_filename.dat')
    data_filepath = latex_directory_path + data_filename

    fout = open(data_filepath, 'w+')

    for instance in dict_sbs_penalty_time_on_each_instance:
        sbs_penalty_time = dict_sbs_penalty_time_on_each_instance[instance]
        sparkle_penalty_time = (
            dict_actual_parallel_portfolio_penalty_time_on_each_instance[instance])
        fout.write(str(sbs_penalty_time) + ' ' + str(sparkle_penalty_time) + '\n')
    fout.close()

    penalised_time_str = str(sgh.settings.get_penalised_time())

    gnuplot_command = (
        f'cd {latex_directory_path}; python auto_gen_plot.py {data_filename} '
        f'{penalised_time_str} \'SBS ({sgrh.underscore_for_latex(sbs_solver)})\' '
        f'Parallel-Portfolio {figure_filename}')

    os.system(gnuplot_command)

    str_value = f'\\includegraphics[width=0.6\\textwidth]{{{figure_filename}}}'

    return (str_value, dict_all_solvers,
            dict_actual_parallel_portfolio_penalty_time_on_each_instance)


def get_resultsTable(results: dict[str, float], parallel_portfolio_path: Path,
                     dict_portfolio: dict[str, float],
                     solver_with_solutions: dict[str, int],
                     n_unsolved_instances: int, n_instances: int) -> str:
    """Return a string containing LaTeX code for a table with the portfolio results."""
    portfolio_PAR10 = 0.0

    for instance in dict_portfolio:
        portfolio_PAR10 += dict_portfolio[instance]

    # Table 1: Portfolio results
    table_string = (
        '\\caption *{\\textbf{Portfolio results}} \\label{tab:portfolio_results} ')
    table_string += '\\begin{tabular}{rrrrr}'
    table_string += (
        '\\textbf{Portfolio nickname} & \\textbf{PAR10} & \\textbf{\\#Timeouts} & '
        '\\textbf{\\#Cancelled} & \\textbf{\\#Best solver} \\\\ \\hline ')
    table_string += (
        f'{sgrh.underscore_for_latex(parallel_portfolio_path.name)} & '
        f'{str(round(portfolio_PAR10,2))} & {str(n_unsolved_instances)} & 0 & '
        f'{str(n_instances-n_unsolved_instances)} \\\\ ')
    table_string += '\\end{tabular}'
    table_string += '\\bigskip'
    # Table 2: Solver results
    table_string += '\\caption *{\\textbf{Solver results}} \\label{tab:solver_results} '
    table_string += '\\begin{tabular}{rrrrr}'

    for i, line in enumerate(results):
        solver_name = sfh.get_last_level_directory_name(line)

        if i == 0:
            table_string += (
                '\\textbf{Solver} & \\textbf{PAR10} & \\textbf{\\#Timeouts} & '
                '\\textbf{\\#Cancelled} & \\textbf{\\#Best solver} \\\\ \\hline ')

        if solver_name not in solver_with_solutions:
            cancelled = n_instances - n_unsolved_instances
            table_string += (
                f'{sgrh.underscore_for_latex(solver_name)} & '
                f'{str(round(results[line], 2))} & {str(n_unsolved_instances)} & '
                f'{str(cancelled)} & 0 \\\\ ')
        else:
            cancelled = (n_instances - n_unsolved_instances
                         - solver_with_solutions[solver_name])
            table_string += (
                f'{sgrh.underscore_for_latex(solver_name)} & '
                f'{str(round(results[line], 2))} & {str(n_unsolved_instances)} & '
                f'{str(cancelled)} & {str(solver_with_solutions[solver_name])} \\\\ ')
    table_string += '\\end{tabular}'

    return table_string


def get_dict_variable_to_value(parallel_portfolio_path: Path,
                               instances: list[str]) -> dict[str, str]:
    """Return a dictionary that maps variables used in the LaTeX report to values."""
    mydict = {}

    variable = 'customCommands'
    str_value = sgrh.get_customCommands()
    mydict[variable] = str_value

    variable = 'sparkle'
    str_value = sgrh.get_sparkle()
    mydict[variable] = str_value

    variable = 'numSolvers'
    str_value = get_numSolvers(parallel_portfolio_path)
    mydict[variable] = str_value

    variable = 'solverList'
    str_value = get_solverList(parallel_portfolio_path)
    mydict[variable] = str_value

    variable = 'numInstanceClasses'
    str_value = get_num_instance_classes(instances)
    mydict[variable] = str_value

    variable = 'instanceClassList'
    str_value, nr_of_instances = get_instanceClassList(instances)
    mydict[variable] = str_value

    variable = 'cutoffTime'
    str_value = str(sgh.settings.get_general_target_cutoff_time())
    mydict[variable] = str_value

    variable = 'solversWithSolution'
    str_value, solvers_with_solution, unsolved_instances = get_solversWithSolution()
    mydict[variable] = str_value

    variable = 'figure-parallel-portfolio-sparkle-vs-sbs'
    (str_value, dict_all_solvers,
        dict_actual_parallel_portfolio_penalty_time_on_each_instance) = (
        get_figure_parallel_portfolio_sparkle_vs_sbs(parallel_portfolio_path, instances))
    mydict[variable] = str_value

    variable = 'resultsTable'
    str_value = get_resultsTable(
        dict_all_solvers, parallel_portfolio_path,
        dict_actual_parallel_portfolio_penalty_time_on_each_instance,
        solvers_with_solution, unsolved_instances, nr_of_instances)
    mydict[variable] = str_value

    variable = 'decisionBool'
    str_value = r'\decisiontrue'

    if(sgh.settings.get_general_performance_measure()
            == PerformanceMeasure.QUALITY_ABSOLUTE):
        str_value = r'\decisionfalse'
    mydict[variable] = str_value

    return mydict


def generate_report(parallel_portfolio_path: Path, instances: list[str]):
    """Generate a report for a parallel algorithm portfolio."""
    latex_report_filename = Path('Sparkle_Report')
    dict_variable_to_value = get_dict_variable_to_value(parallel_portfolio_path,
                                                        instances)

    latex_directory_path = Path(
        'Components/Sparkle-latex-generator-for-parallel-portfolio/')
    latex_template_filename = Path('template-Sparkle.tex')
    latex_template_filepath = Path(latex_directory_path / latex_template_filename)
    report_content = ''

    with open(latex_template_filepath, 'r') as infile:
        for line in infile:
            report_content += line

    for variable_key, str_value in dict_variable_to_value.items():
        variable = '@@' + variable_key + '@@'
        report_content = report_content.replace(variable, str_value)

    latex_report_filepath = Path(latex_directory_path / latex_report_filename)
    latex_report_filepath = latex_report_filepath.with_suffix('.tex')

    with open(latex_report_filepath, 'w+') as outfile:
        for line in report_content:
            outfile.write(line)

    file_path_output = PurePath(sgh.sparkle_global_output_dir / sl.caller_out_dir
                                / 'Log/latex.txt')
    sfh.create_new_empty_file(file_path_output)
    file_path_output = Path('../../' / file_path_output)
    compile_command = (f'cd {latex_directory_path}; pdflatex {latex_report_filename}.tex'
                       f' 1> {file_path_output} 2>&1')
    os.system(compile_command)
    os.system(compile_command)

    compile_command = (f'cd {latex_directory_path}; bibtex {latex_report_filename}.aux '
                       f'1> {file_path_output} 2>&1')
    os.system(compile_command)
    os.system(compile_command)

    compile_command = (f'cd {latex_directory_path}; pdflatex {latex_report_filename}.tex'
                       f' 1> {file_path_output} 2>&1')
    os.system(compile_command)
    os.system(compile_command)

    report_path = Path(f'{latex_directory_path}{latex_report_filename}.pdf')
    print(f'c Report is placed at: {report_path}')
    sl.add_output(str(report_path), 'Sparkle parallel portfolio report')

    return
