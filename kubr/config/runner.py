from dataclasses import field
from typing import Dict, List, Literal, Union
from typing import Optional

from pydantic import BaseModel


class ContainerConfig(BaseModel):
    """ ContainerConfig is the configuration for the container.

    Args:
        image (str): Image to run.
        entrypoint (str): Entrypoint to run.
        env (Dict[str, str], optional): Environment variables to pass to the entrypoint. Defaults to {}.

    """
    image: str
    entrypoint: str
    env: Dict[str, str] = field(default_factory=dict)
    port_map: Dict[str, int] = field(default_factory=dict)
    args: List[str] = field(default_factory=list)
    python_path: str = ""


class GitConfig(BaseModel):
    url: str
    branch: str
    commit: str
    secret: str


class VolumeMount(BaseModel):
    """VolumeMount is the configuration for a volume mount.

    Args:
        name (str): Name of the volume.
        type (Literal["pvc", "hostPath"]): Type of the volume.
        mount_path (str): Mount path of the volume.
    """
    name: str
    type: Literal["pvc", "hostPath"]
    mount_path: str


class CodePersistenceConfig(BaseModel):
    git: Optional[GitConfig] = None
    pvc: Optional[str] = None
    volume: Optional[VolumeMount] = None


class DataConfig(BaseModel):
    """DataConfig is the configuration for the data.

    Args:
        pvcs (Optional[List[str]], optional): List of PVCs to mount. Defaults to None.
        volumes (Optional[List[VolumeMount]], optional): List of volumes to mount. Defaults to None.
    """
    pvcs: Optional[List[str]] = None
    volumes: Optional[List[VolumeMount]] = None


class ResourceConfig(BaseModel):
    """ResourceConfig is the configuration for the resources.

    Args:
        num_replicas (int, optional): Number of replicas to run. Defaults to 1.
        cpu (int, optional): Number of CPUs to request. Defaults to 0.
        memMB (int, optional): Memory in MB to request. Defaults to 0.
        gpu (int, optional): Number of GPUs to request. Defaults to 0.
        ib (Union[int, Literal['auto']], optional): Number of Infiniband devices to request. Defaults to 0.
        ib_device (str, optional): Name of the Infiniband device to request. Defaults to "nvidia.com/hostdev".
    """
    num_replicas: int = 1
    cpu: int = 0
    memMB: int = 0
    gpu: int = 0
    devices: Dict[str, float] = field(default_factory=dict)
    capabilities: Dict[str, str] = field(default_factory=dict)
    ib: Union[int, Literal['auto']] = 0
    ib_device: str = "nvidia.com/hostdev"


class ExperimentConfig(BaseModel):
    """ExperimentConfig is the configuration for the experiment.

    Args:
        name (str): Name of the experiment.
        namespace (str): Namespace of the experiment.
        args (List[str], optional): Arguments to pass to the entrypoint. Defaults to [].
        env (Dict[str, str], optional): Environment variables to pass to the entrypoint. Defaults to {}.
        queue (Optional[str], optional): Queue to submit the experiment to. Defaults to "default".
        priority_class (Optional[str], optional): Priority class to submit the experiment to. Defaults to None.
        job_retries (int, optional): Number of retries for the job. Defaults to 0.
        min_replicas (int, optional): Minimum number of replicas to run. Defaults to 1.
        task_name (str, optional): Name of the task. Defaults to "main-task".
        task_max_retries (int, optional): Maximum number of retries for the task. Defaults to 10.
    """
    name: str
    namespace: str

    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

    queue: Optional[str] = "default"
    priority_class: Optional[str] = None

    job_retries: int = 0
    min_replicas: int = 1
    task_name: str = "main-task"
    task_max_retries: int = 10


class RunnerConfig(BaseModel):
    """RunnerConfig is the configuration for the runner.

    Args:
        experiment (ExperimentConfig): Experiment configuration.
        container (ContainerConfig): Container configuration.
        resources (ResourceConfig): Resource configuration.
        type (Literal["Volcano"], optional): Type of runner. Defaults to "Volcano".
        code (Optional[CodePersistenceConfig], optional): Code persistence configuration. Defaults to None.
        data (Optional[DataConfig], optional): Data configuration. Defaults to None.

    """
    experiment: ExperimentConfig
    container: ContainerConfig
    resources: ResourceConfig
    type: Literal["Volcano"] = "Volcano"
    code: Optional[CodePersistenceConfig] = None
    data: Optional[DataConfig] = None
