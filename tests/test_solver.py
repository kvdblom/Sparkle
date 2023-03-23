"""Test public methods of solver class."""

import shutil

from unittest import TestCase, mock
from pathlib import Path

from Commands.sparkle_help.solver import Solver


class TestSolver(TestCase):
    def setUp(self):
        self.solver_path = Path("tests", "test_files", "test_solver")
        self.solver_path.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.solver_path)

    def test_init_variables(self):
        solver = Solver(Path("test/directory/solver_executable"))

        self.assertEqual(solver.directory, Path("test/directory/solver_executable"))
        self.assertEqual(solver.name, "solver_executable")
        pass

    def test_pcs_file_correct_name(self):
        file = open(self.solver_path / "paramfile.pcs", "w")
        file.close()

        solver = Solver(self.solver_path)

        self.assertEqual(solver.get_pcs_file(), "paramfile.pcs")

    def test_pcs_file_none(self):
        solver = Solver(self.solver_path)

        with self.assertRaises(SystemExit):
            solver.get_pcs_file()

    def test_pcs_file_multiple(self):
        file = open(self.solver_path / "paramfile1.pcs", "w")
        file.close()

        file = open(self.solver_path / "paramfile2.pcs", "w")
        file.close()

        solver = Solver(self.solver_path)

        with self.assertRaises(SystemExit):
            solver.get_pcs_file()

    def test_is_deterministic_false(self):
        file_string = "Solvers/test_solver 0 1"
        solver = Solver(self.solver_path)

        with mock.patch("builtins.open",
                        mock.mock_open(read_data=file_string)) as mock_file:
            self.assertEqual(solver.is_deterministic(), "0")
            mock_file.assert_called_with("Reference_Lists/sparkle_solver_list.txt", "r+")

    def test_is_deterministic_true(self):
        file_string = "Solvers/test_solver 1 1"
        solver = Solver(self.solver_path)

        with mock.patch("builtins.open",
                        mock.mock_open(read_data=file_string)) as mock_file:
            self.assertEqual(solver.is_deterministic(), "1")
            mock_file.assert_called_with("Reference_Lists/sparkle_solver_list.txt", "r+")
