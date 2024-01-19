from kubr.commands.base import BaseCommand


class TestCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers, completer):
        test_parser = subparsers.add_parser("test", help="Test a job")
        return test_parser

    def __call__(
        self,
    ):
        raise NotImplementedError
