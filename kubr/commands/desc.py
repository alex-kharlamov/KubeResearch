from kubr.backends.volcano import VolcanoBackend
from kubr.commands.base import BaseCommand


class DescribeCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers, completer):
        desc_parser = subparsers.add_parser('desc', help='Get info about a job')
        desc_parser.add_argument('job_name', help='Name of job to get info about').completer = completer
        desc_parser.add_argument('-n', '--namespace', help='Namespace to get info from', default='default')
        return desc_parser

    def __call__(self, *args, **kwargs):
        return self.backend.describe_job(*args, **kwargs)
