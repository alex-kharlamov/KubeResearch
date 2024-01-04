from kubr.backends.volcano import VolcanoBackend


class RUNOperator:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()
    def __call__(self, *args, **kwargs):
        return self.backend.run_job(*args, **kwargs)