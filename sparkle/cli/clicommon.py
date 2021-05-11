# Python libs
from dataclasses import dataclass
from argparse import ArgumentParser


class Command:
    def __init__(self, name, description, help, actions=[]):
        self.name = name
        self.description = description
        self.help = help
        self.actions = {action.name: action for action in actions}

    def add_parsing(self, parser: ArgumentParser):
        self.parser = parser
        subparsers = parser.add_subparsers(
            help = "actions",
            dest = "action",
            )

        for name, action in self.actions.items():
            action.add_parsing(
                subparsers.add_parser(
                    name = name,
                    description = action.description,
                    conflict_handler = "resolve"
                ))

    def dispatch(self, args):
        if args.action is None:
            self.no_action(args)
        elif args.action not in self.actions:
            print("Error. Non valid action.")
        else:
            self.actions[args.action].do(args)

    def no_action(self, args):
        # By default, if no action is set, show help.
        self.parser.print_help()


@dataclass
class Action:
    name: str          # The name of the command
    description: str   # The description of the command

    def add_parsing(self, parser: ArgumentParser):
        pass

    def do(self, args):
        print(f"Action not implemented for 'sparkle {args.command} {args.action}'.")
        print(args)