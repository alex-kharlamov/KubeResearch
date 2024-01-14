from typing import Optional

from kubr.backends.volcano import VolcanoBackend


class LogsCommand:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    @staticmethod
    def add_parser(subparsers, completer):
        logs_parser = subparsers.add_parser('logs', help='Get logs of a job')
        logs_parser.add_argument('job',
                                 help='Name of job to get logs of').completer = completer
        logs_parser.add_argument('-n', '--namespace', help='Namespace to get logs from', default='default')
        logs_parser.add_argument('-t', '--tail', help='Number of lines to show', default=10, type=int)
        return logs_parser

    def __call__(self, job_name: str, namespace: str, tail: Optional[int] = None):
        return self.backend.get_logs(job_name=job_name, namespace=namespace, tail=tail)
