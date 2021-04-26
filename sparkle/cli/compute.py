# Python libs
from dataclasses import dataclass
from argparse import ArgumentParser

# Sparkle libs
from .clicommon import Command
from .clicommon import Action


@dataclass
class Compute(Command):
    name: str = "compute"
    description: str = "Manage the computing units"
    help: str = "Manage the computing units"
    
    def get_actions(self) -> list : 
        return [Add(), ]

    def no_action(self):
        print("No action. Print info.")

@dataclass
class Add(Action):
    name: str = "add"
    description: str = "Add compute unit"

    def add_parsing(self, parser: ArgumentParser):
        parser.add_argument("--name")

    def action(self, name):
        print(f"This is action 'compute add' on {name}")