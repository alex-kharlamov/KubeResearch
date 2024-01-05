from typing import Optional

from kubr.backends.volcano import VolcanoBackend
class LOGSOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def __call__(self, job_name: str, namespace: str, tail: Optional[int] = None):
        return self.backend.get_logs(job_name=job_name, namespace=namespace, tail=tail)