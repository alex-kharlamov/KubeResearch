from kubr.backends.volcano import VolcanoBackend


class BaseCommand:
    def __init__(self, backend=None):
        self.backend = backend or VolcanoBackend()

    @staticmethod
    def add_parser(subparsers, completer=None):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        raise NotImplementedError
