#!/bin/bash

### Use Sparkle for a parallel algorithm portfolio with runtime objective
### The example illustrates the use of a decision algorithm and measures runtime performance

#### Initialise the Sparkle platform

sparkle initialise

#### Add instances 

# Add instances (in this case for the portfolio) in a given directory, without running solvers or feature extractors
# Note that you should use the full path to the directory containing the instance(s)

sparkle add_instances Examples/Resources/Instances/PTN/

#### Add solvers

# Add a solver without running the solver yet
# The path used should be the full path to the solver directory and should contain the solver executable and the `sparkle_smac_wrapper` wrapper

# If needed solvers can also include additional files or scripts in their directory, but try to keep additional files to a minimum as it speeds up copying.
# Use the --solver-variations option to set the default number of solver variations of a solver which will be used when a portfolio is constructed. E.g. '--solver-variations 5'

sparkle add_solver --deterministic 0 Examples/Resources/Solvers/CSCCSat/
sparkle add_solver --deterministic 0 Examples/Resources/Solvers/MiniSAT/
sparkle add_solver --deterministic 0 Examples/Resources/Solvers/PbO-CCSAT-Generic/

#### Construct the portfolio

# The construction of the portfolio uses all the added solvers in the Solver/ directory and keeps in mind the --overwrite setting.
# By default --overwrite is set to false, which means an existing portfolio with the same name cannot be overwritten and will throw an error instead. If set to true, an existing portfolio with the same name will be overwritten (if it exists)

# The --nickname option can be used to name your portfolio.
# For example '--nickname runtime_experiment', if this option is not used then the default nickname is used, which is 'sparkle_parallel_portfolio'
# Without using the --solver option ALL solvers will be added, if you want, for example, only a subset of solvers from the Solver/ directory 
# you can use a space separated list, like '--solver Solvers/CSCCSat Solvers/PbO-CCSAT-Generic'

# In order to add multiple variations of a single solver you have to add ',<number_of_solver_variations>' within the space separated solver list.
# For example '--solver Solvers/PbO-CCSAT-Generic,4' which will create a portfolio containing four variations of PbO-CCSAT-Generic
# If this is not used only a single variation of the solver will be added

sparkle construct_sparkle_parallel_portfolio --nickname runtime_experiment

#### Run the portfolio 

# By running the portfolio a list of jobs will be created which will be executed by the cluster.
# Use the --cutoff-time option to specify the maximal time for which the portfolio is allowed to run.
# add --portfolio-name to specify a portfolio otherwise it will select the last constructed portfolio

# The --instance-paths option must be followed by a space separated list of paths to an instance or an instance set.
# For example --instance-paths Instances/Instance_Set_Name/Single_Instance Instances/Other_Instance_Set_Name

sparkle run_sparkle_parallel_portfolio --instance-paths Instances/PTN/ --portfolio-name runtime_experiment

#### Generate the report

# The report details the experimental procedure and performance information. 
# This will be located at Components/Sparkle-latex-generator-for-parallel-portfolio/Sparkle_Report.pdf

sparkle generate_report
