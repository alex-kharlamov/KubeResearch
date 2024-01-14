from kubr.backends.volcano import VolcanoBackend
from kubr.commands.base import BaseCommand


class RmCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers, completer):
        rm_parser = subparsers.add_parser('rm', help='Delete a job')
        rm_parser.add_argument('job', help='Name of job to delete').completer = completer
        rm_parser.add_argument('-n', '--namespace', help='Namespace to delete job from', default='default')
        return rm_parser

    def __call__(self, job_name: str, namespace: str = 'default'):
        return self.backend.delete_job(job_name=job_name, namespace=namespace)
