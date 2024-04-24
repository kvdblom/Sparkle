#!/bin/bash

### Use Sparkle for algorithm configuration

#### Initialise the Sparkle platform

CLI/initialise.py

#### Add instances

# Add train, and optionally test, instances (in this case for the VRP) in a given directory, without running solvers or feature extractors yet

CLI/add_instances.py Examples/Resources/CVRP/Instances/X-1-10/
CLI/add_instances.py Examples/Resources/CVRP/Instances/X-11-20/

#### Add a configurable solver

# Add a configurable solver (here for vehicle routing) with a wrapper containing the executable name of the solver and a string of command line parameters, without running the solver yet

# The solver directory should contain the solver executable, the `sparkle_smac_wrapper.py` wrapper, and a `.pcs` file describing the configurable parameters

CLI/add_solver.py --deterministic 0 Examples/Resources/CVRP/Solvers/VRP_SISRs/

# If needed solvers can also include additional files or scripts in their directory, but keeping additional files to a minimum speeds up copying.

#### Configure the solver

# Perform configuration on the solver to obtain a target configuration. For the VRP we measure the absolute quality performance by setting the `--performance-measure` option, to avoid needing this for every command it can also be set in `Settings/sparkle_settings.ini`.

CLI/configure_solver.py --solver Solvers/VRP_SISRs/ --instance-set-train Instances/X-1-10/ --performance-measure QUALITY_ABSOLUTE

#### Validate the configuration

# To make sure configuration is completed before running validation you can use the sparkle_wait command

CLI/sparkle_wait.py

# Validate the performance of the best found parameter configuration. The test set is optional. We again set the performance measure to absolute quality.

CLI/validate_configured_vs_default.py --solver Solvers/VRP_SISRs/ --instance-set-train Instances/X-1-10/ --instance-set-test Instances/X-11-20/ --performance-measure QUALITY_ABSOLUTE

#### Generate a report

# Wait for validation to be completed

CLI/sparkle_wait.py

# Generate a report detailing the results on the training (and optionally testing) set. This includes the experimental procedure and performance information; this will be located in a `Configuration_Reports/` subdirectory for the solver, training set, and optionally test set like `VRP_SISRs_X-1-10_X-11-20/Sparkle-latex-generator-for-configuration/`. We again set the performance measure to absolute quality.

CLI/generate_report.py --performance-measure QUALITY_ABSOLUTE

# By default the `generate_report` command will create a report for the most recent solver and instance set(s). To generate a report for older solver-instance set combinations, the desired solver can be specified with `--solver Solvers/CVRP/VRP_SISRs/`, the training instance set with `--instance-set-train Instances/CVRP/X-1-10/`, and the testing instance set with `--instance-set-test Instances/CVRP/X-11-20/`.

