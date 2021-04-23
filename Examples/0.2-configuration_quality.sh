#!/bin/bash

# Use Sparkle for algorithm configution

## Initialise the Sparkle platform

sparkle init algoconf-example
cd algoconf-example

## Add compute units

sparkle compute

sparkle compute add slurm --conf=slurm.conf

## Add instances

# Add train, and optionally test, instances (in this case for the VRP) in a given directory, without running solvers or feature extractors yet

sparkle instance add iset1 Examples/Resources/CVRP/Instances/X-1-10
sparkle instance add iset2 Examples/Resources/CVRP/Instances/X-11-20
sparkle instance add ifull Examples/Resources/CVRP/Instances/*


## Add a configurable solver

# Add a configurable solver (here for vehicle routing) with a wrapper containing the executable name of the solver and a string of command line parameters, without running the solver yet

# The solver directory should contain the solver executable, the `sparkle_smac_wrapper.py` wrapper, and a `.pcs` file describing the configurable parameters

sparkle solver add VRP Examples/Resources/Solvers/CVRP/VRP_SISRs


## Configure the solver

# Perform configuration on the solver to obtain a target configuration. For the VRP we measure the absolute quality performance by setting the `--performance-measure` option, to avoid needing this for every command it can also be set in `Settings/sparkle_settings.ini`.

# sparkle solver configure VRP --train=iset1 --metric=quality --runon=slurm

sparkle solver configure VRP --train=iset1 --metric=quality --runon=local --wait

## Validate the configuration

# To make sure configuration is completed before running validation you can use the sparkle_wait command


sparkle status 

sparkle wait

# Validate the performance of the best found parameter configuration. The test set is optional. We again set the performance measure to absolute quality.

sparkle solver validate VRP --train=iset1 --test=iset2 --metric=quality --runon=slurm --wait

#### Generate a report


# Generate a report detailing the results on the training (and optionally testing) set. This includes the experimental procedure and performance information; this will be located in a `Configuration_Reports/` subdirectory for the solver, training set, and optionally test set like `VRP_SISRs_X-1-10/Sparkle-latex-generator-for-configuration/`. We again set the performance measure to absolute quality.

sparkle report --metric=quality --solver=VRP --train=iset1 --test=iset2

# By default the `generate_report` command will create a report for the most recent solver and instance set(s). To generate a report for older solver-instance set combinations, the desired solver can be specified with `--solver Solvers/CVRP/VRP_SISRs/`, the training instance set with `--instance-set-train Instances/CVRP/X-1-10/`, and the testing instance set with `--instance-set-test Instances/CVRP/X-11-20/`.



