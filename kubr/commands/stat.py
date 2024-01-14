from kubr.commands.base import BaseCommand


class StatCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers, completer):
        stat_parser = subparsers.add_parser('stat', help='Get statistics about a job')
        stat_parser.add_argument('job', help='Name of job to get statistics about').completer = completer
        stat_parser.add_argument('-n', '--namespace', help='Namespace to get statistics from', default='default')
        return stat_parser

    def __call__(self, job_name: str, namespace: str = 'default'):
        raise NotImplementedError
