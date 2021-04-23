#!/bin/bash

# Use Sparkle for algorithm configution

## Initialise the Sparkle platform

sparkle init selection-example
cd selection-example

## Add compute units

# To list the availtible compute unit:
sparkle compute

# By default, the local unit is always availible and unless specified by a --runon=, the 
# computation are done on the local compute unit and the flag --wait is imply to wait for 
# the end of the computation before the command return

# To add a cluster
sparkle compute add slurm --conf=../slurm.conf


## Add instances

# Add instance files (in this case in CNF format) in a given directory, without running solvers or feature extractors yet

sparkle instance add ptn ../Examples/Resources/Instances/PTN
sparkle instance add ptn2 ../Examples/Resources/Instances/PTN2
sparkle instance add ptn2-7824 ../Examples/Resources/Instances/PTN2/plain7824.cnf


## Add solvers

# Add solvers (here for SAT solving) with a wrapper containing the executable name of the solver and a string of command line parameters, without running the solvers yet

# Each solver directory should contain the solver executable and a wrapper

sparkle solve add CSCCSat ../Examples/Resources/Solvers/CSCCSat
sparkle solve add PbO ../Examples/Resources/Solvers/PbO-CCSAT-Generic
sparkle solve add MiniSAT ../Examples/Resources/Solvers/MiniSAT


## Add feature extractor

# Similarly, add a feature extractor, without immediately running it on the instances

sparkle feature add comp2012 ../Examples/Resources/Extractors/SAT-features-competition2012_revised_without_SatELite_sparkle/

# Compute features for all the instances; add the `--parallel` option to run in parallel

sparkle feature compute --all --runon=slurm --wait

## Run the solvers

# Run the solvers on all instances; add the `--parallel` option to run in parallel

sparkle solver run --all --runon=slurm --wait

# Construct a portfolio selector, using the previously computed features and the results of running the solvers

sparkle portfolio generate port1 --all


## Generate a report

# Generate an experimental report detailing the experimental procedure and performance information; this will be located at `Components/Sparkle-latex-generator/Sparkle_Report.pdf`

sparkle report --portfolio=port1


# Run the portfolio selector (e.g. on a test set)

## Run on a single instance

# Run the portfolio selector on a *single* testing instance; the result will be printed to the command line

sparkle portfolio port1 --instance=ptn2-7824 --runon=slurm --wait


## Run on an instance set

# Run the portfolio selector on a testing instance *set*

sparkle portfolio port1 --instance=ptn2 --runon=slurm


## Generate a report including results on the test set

# Wait for the portfolio selector to be done running on the testing instance set

sparkle wait

# Generate an experimental report that includes the results on the test set, and as before the experimental procedure and performance information; this will be located at `Components/Sparkle-latex-generator/Sparkle_Report_For_Test.pdf`

sparkle report --portfolio=port1 --instance=ptn2



