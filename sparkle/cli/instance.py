# Python libs
from dataclasses import dataclass
from argparse import ArgumentParser

# Sparkle libs
from .clicommon import Command
from .clicommon import Action


@dataclass
class Instance(Command):
    name: str = "instance"
    description: str = "Manage the instances"
    help: str = "Manage the instances"
    
    def get_actions(self) -> list : 
        return [Add(), ]

@dataclass
class Add(Action):
    name: str = "add"
    description: str = "Add instances unit"

    def add_parsing(self, parser: ArgumentParser):
        parser.add_argument("--name")

    #def action(self, name):
        #print(f"This is action 'compute add' on {name}")