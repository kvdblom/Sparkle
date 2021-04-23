from argparse import ArgumentParser


class SparkleParser(ArgumentParser):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)



class ComputeParser(ArgumentParser):
    name = "compute"
    description = "Manage the computing units"

    def __init__(self):
        super().__init__()

        subparser = self.add_subparsers(
            help = "subcommands",
            dest = "subcommand"
            )

        for parser in [ComputeAddParser, ]:
            subparser.add_parser(
                name = parser.name,
                parents = [parser(), ],
                description = parser.description,
                conflict_handler = "resolve"
            )



class ComputeAddParser(ArgumentParser):
    name = "add"
    description = "Add compute unit"
    
    def __init__(self):
        super().__init__()



class InstanceParser(ArgumentParser):
    name = "instance"
    description = "Manage the instance sets",

    def __init__(self):
        super().__init__()