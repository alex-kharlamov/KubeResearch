from enum import Enum


class PrettyEnum(Enum):
    def __str__(self):
        return str(self.value)


class DeleteStatus(PrettyEnum):
    """DeleteStatus is the status of the job deletion.

    Args:
        Success (str): Job was deleted successfully.
        Failed (str): Job deletion failed.
    """
    Success = "Success"
    Failed = "Failed"


class BaseBackend:
    def __init__(self):
        pass

    def run_job(self, *args, **kwargs):
        raise NotImplementedError

    def list_jobs(self, *args, **kwargs):
        raise NotImplementedError

    def delete_jobs(self, *args, **kwargs):
        raise NotImplementedError

    def get_logs(self, *args, **kwargs):
        raise NotImplementedError

    def describe_job(self, *args, **kwargs):
        raise NotImplementedError
