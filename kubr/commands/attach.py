from kubr.commands.base import BaseCommand


class AttachCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers, completer):
        attach_parser = subparsers.add_parser("attach", help="Attach to a running job")
        attach_parser.add_argument("job", help="Name of job to attach to").completer = completer
        attach_parser.add_argument("-n", "--namespace", help="Namespace to attach to", default="default")
        return attach_parser

    def __call__(self, job_name: str, namespace: str = "default"):
        raise NotImplementedError
