from argparse import ArgumentParser

class MainParser(ArgumentParser):
    def __init__(self, subparsers: list):
        super().__init__()
        self.subparsers = {s.name: s for s in subparsers}

        adder = self.add_subparsers(
            title = "Sparkle commands",
            help = "commands",
            dest = "command",
            parser_class = ArgumentParser
            )

        for parser in subparsers:
            sub = adder.add_parser(
                parser.name,
                description = parser.description,
                help = parser.help,
                conflict_handler = "resolve"
            )
            parser.add_parsing(sub)

    def dispatch(self, args):
        self.subparsers[args.command].execute(args)
