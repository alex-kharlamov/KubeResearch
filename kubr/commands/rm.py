from rich import print

from kubr.backends.base import JobOperationStatus
from kubr.commands.base import BaseCommand
from kubr.commands.utils.drawing import mascot_message


class RmCommand(BaseCommand):
    @staticmethod
    def add_parser(subparsers, completer):
        rm_parser = subparsers.add_parser("rm", help="Delete a job")
        rm_parser.add_argument("job", help="Name of job to delete").completer = completer
        rm_parser.add_argument("-n", "--namespace", help="Namespace to delete job from", default="default")
        return rm_parser

    def __call__(self, job_name: str, namespace: str = "default"):
        # TODO [rm] add regular expression matching for job names
        # TODO [rm] add confirmation prompt
        # TODO [rm] add completion for namespace typing
        try:
            status = self.backend.delete_job(job_name=job_name, namespace=namespace)
        except Exception:
            print(mascot_message(f"Job {job_name} deletion failed!"))
            return

        if status == JobOperationStatus.Success:
            print(mascot_message(f"Job {job_name} was deleted successfully!"))
