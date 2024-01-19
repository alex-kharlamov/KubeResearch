import datetime
from typing import Union

from pydantic import BaseModel

from kubr.backends.base import PrettyEnum


class JobType(PrettyEnum):
    """JobType is the type of job to run.

    Args:
        torchrun (str): Run a torchrun job.
    """

    torchrun = "torchrun"


class JobBackend(PrettyEnum):
    """JobBackend is the type of job to run.

    Args:
        Volcano (str): Run a Volcano job.
    """

    Volcano = "Volcano"


class JobState(PrettyEnum):
    """JobState is the state of the job.

    Args:
        Pending (str): Job is pending.
        Running (str): Job is running.
        Completed (str): Job is completed.
        Failed (str): Job has failed.
    """

    Pending = "Pending"
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"


class Job(BaseModel):
    type: JobType
    backend: JobBackend
    name: str
    namespace: str
    state: JobState
    age: Union[datetime.datetime, str]
    gpu: int
    nodes: int = 1
