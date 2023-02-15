#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Configurator class to use different configurators like SMAC."""

import os
import sys
import fcntl

from pathlib import Path

from sparkle_help import sparkle_global_help as sgh


class Solver:
    def __init__(self, solver_directory: Path) -> None:
        self.directory = solver_directory
        self.name = solver_directory.name
        self.pcs_file = (self.directory / self.get_pcs_file())
        self.is_deterministic = self.get_solver_deterministic()

    def get_pcs_file(self) -> Path:
        """."""
        file_count = 0
        file_name = ""
        for file_path in self.directory.iterdir():
            file_extension = "".join(file_path.suffixes)

            if file_extension == ".pcs":
                file_name = file_path.name
                file_count += 1

        if file_count != 1:
            print(
                "None or multiple .pcs files found. Solver is not valid for configuration."
            )
            sys.exit()

        return file_name

    def get_solver_deterministic(self) -> str:
        """Return a str indicating whether a given solver is deterministic or not."""
        deterministic = ""
        target_solver_path = "Solvers/" + self.name
        solver_list_path = sgh.solver_list_path

        fin = open(solver_list_path, "r+")
        fcntl.flock(fin.fileno(), fcntl.LOCK_EX)

        while True:
            myline = fin.readline()
            if not myline:
                break
            myline = myline.strip()
            mylist = myline.split()

            if (mylist[0] == target_solver_path):
                deterministic = mylist[1]
                break

        return deterministic