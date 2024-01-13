from kubr.backends.volcano import VolcanoBackend

class DESCOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    def __call__(self, *args, **kwargs):
        return self.backend.describe_job(*args, **kwargs)