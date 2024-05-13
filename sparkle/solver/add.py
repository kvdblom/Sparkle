#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Helper functions for adding solvers."""
import os
from pathlib import Path
import global_variables as sgh


def get_solver_directory(solver_name: str) -> str:
    """Return the directory a solver is stored in as str.

    Args:
        solver_name: Name of the solver.

    Returns:
        A str of the path to the solver.
    """
    return str(sgh.solver_dir / solver_name)
