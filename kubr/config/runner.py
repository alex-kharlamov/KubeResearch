from typing import List, Literal, Optional, Union

import pydantic
from pydantic import BaseModel

from kubr.config.job import JobBackend, JobType


class SecretMount(BaseModel):
    env: str
    secret_namespace: str
    secret_name: str
    secret_key: str


class EnvVar(BaseModel):
    """EnvVar is the configuration for an environment variable.

    Args:
        name (str): Name of the environment variable.
        value (str): Value of the environment variable.
    """

    name: str
    value: str


class ContainerConfig(BaseModel):
    """ContainerConfig is the configuration for the container.

    Args:
        image (str): Image to run.
        entrypoint (Optional[str], optional): Entrypoint to run. Defaults to None.
        env (Dict[str, str], optional): Environment variables to pass to the entrypoint. Defaults to {}.
        secrets (Optional[List[SecretConfig]], optional): Secrets to pass to the entrypoint. Defaults to None.
    """

    image: str
    entrypoint: Optional[str] = None
    env: List[EnvVar] = []
    secrets: List[SecretMount] = []
    # port_map: Dict[str, int] = field(default_factory=dict)
    # args: List[str] = field(default_factory=list)
    # python_path: str = ""


class GitConfig(BaseModel):
    url: str
    branch: str
    commit: str


class VolumeMount(BaseModel):
    """VolumeMount is the configuration for a volume mount.

    Args:
        name (str): Name of the volume.
        type (Literal["hostPath"]): Type of the volume.
        mount_path (str): Mount path of the volume.
    """

    name: str
    type: Literal["hostPath"]
    mount_path: str


class CodePersistenceConfig(BaseModel):
    # git: Optional[GitConfig] = None
    # pvc: Optional[str] = None
    volume: Optional[VolumeMount] = None


class DataConfig(BaseModel):
    """DataConfig is the configuration for the data.

    Args:
        volumes (Optional[List[VolumeMount]], optional): List of volumes to mount. Defaults to [].
    """

    # pvcs: Optional[List[str]] = None
    volumes: Optional[List[VolumeMount]] = []


class ResourceConfig(BaseModel):
    """ResourceConfig is the configuration for the resources.

    Args:
        nodes (int, optional): Number of replicas to run. Defaults to 1.
        cpu (int, optional): Number of CPUs to request. Defaults to 0.
        memory (int, optional): Memory in GB to request. Defaults to 0.
        gpu (int, optional): Number of GPUs to request. Defaults to 0.
        ib (Union[int, Literal['auto']], optional): Number of Infiniband devices to request. Defaults to 0.
        ib_device (str, optional): Name of the Infiniband device to request. Defaults to "nvidia.com/hostdev".
    """

    # TODO [config][resources] add taints\tolerations\affinity
    nodes: int = pydantic.Field(gt=0, type=int, default=1)
    cpu: int = 0
    memory: float = 0
    gpu: int = 0
    # devices: Dict[str, float] = field(default_factory=dict)
    # capabilities: Dict[str, str] = field(default_factory=dict)
    ib: Union[int, Literal["auto"]] = 0
    ib_device: str = "nvidia.com/hostdev"


class ExperimentConfig(BaseModel):
    """ExperimentConfig is the configuration for the experiment.

    Args:
        name (str): Name of the experiment.
        namespace (str): Namespace of the experiment.
        queue (Optional[str], optional): Queue to submit the experiment to. Defaults to "default".
        job_retries (int, optional): Number of retries for the job. Defaults to 0.
        worker_max_retries (int, optional): Maximum number of retries for the task. Defaults to 10.
    """

    name: str
    namespace: str

    # args: List[str] = field(default_factory=list)
    # env: Dict[str, str] = field(default_factory=dict)

    queue: Optional[str] = "default"
    # priority_class: Optional[str] = None

    # TODO add tests for retries
    job_retries: int = 0
    worker_max_retries: int = 0


class RunnerConfig(BaseModel):
    """RunnerConfig is the configuration for the runner.

    Args:
        experiment (ExperimentConfig): Experiment configuration.
        container (ContainerConfig): Container configuration.
        resources (ResourceConfig): Resource configuration.
        type (JobType, optional): Job type. Defaults to JobType.torchrun.
        backend (JobBackend, optional): Job backend. Defaults to JobBackend.Volcano.
        code (Optional[CodePersistenceConfig], optional): Code persistence configuration. Defaults to None.
        data (Optional[DataConfig], optional): Data configuration. Defaults to None.

    """

    experiment: ExperimentConfig
    init_container: Optional[ContainerConfig] = None
    container: ContainerConfig
    resources: ResourceConfig
    type: JobType = JobType.torchrun
    backend: JobBackend = JobBackend.Volcano
    code: Optional[CodePersistenceConfig] = None
    data: Optional[DataConfig] = None
