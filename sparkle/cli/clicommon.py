from argparse import ArgumentParser
from dataclasses import dataclass

@dataclass
class Command:
    name: str          # The name of the command
    description: str   # The description of the command
    help: str          # Command help

    def add_parsing(self, parser: ArgumentParser):
        self.parser = parser
        subparsers = parser.add_subparsers(
            help = "actions",
            dest = "action",
            )

        for act in self.get_actions():
            act.add_parsing(
                subparsers.add_parser(
                    name = act.name,
                    description = act.description,
                    conflict_handler = "resolve"
                ))

    #TODO: Change type annotation to a more generic type and including CliAction
    def get_actions(self) -> list:  
        return list()


    def run(self, args):
        pass

    def no_action(self, args):
        # By default, if no action is set, show help.
        pass


@dataclass
class Action:
    name: str          # The name of the command
    description: str   # The description of the command

    def add_parsing(self, parser: ArgumentParser):
        pass

    def actions(self, args):
        print(f"Action no implemented for '{args.command} {args.action}'.")