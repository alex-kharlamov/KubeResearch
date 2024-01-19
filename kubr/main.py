# PYTHON_ARGCOMPLETE_OK
import argparse

import argcomplete

from kubr.backends.volcano import VolcanoBackend
from kubr.commands.desc import DescribeCommand
from kubr.commands.logs import LogsCommand
from kubr.commands.ls import LsCommand
from kubr.commands.rm import RmCommand
from kubr.commands.run import RunCommand


def main():
    # TODO fix package install adding eval in bash\zsh for autocomplete
    # adding eval "$(register-python-argcomplete kubr)" to .bashrc or .zshrc
    # TODO fix autopilot deployment in GKE autopilot
    # TODO fix Volcano priority class in GKE (https://github.com/volcano-sh/volcano/issues/2379)

    backend = VolcanoBackend()
    arg = argparse.ArgumentParser(description="Kubr", add_help=True)
    arg.add_argument("--version", help="Get version of Kubr")
    subparsers = arg.add_subparsers(help="Commands", dest="command")

    RunCommand.add_parser(subparsers)
    LsCommand.add_parser(subparsers)
    RmCommand.add_parser(subparsers, completer=backend._completion_list_running_jobs)
    DescribeCommand.add_parser(subparsers, completer=backend._completion_list_running_jobs)
    LogsCommand.add_parser(subparsers, completer=backend._completion_list_running_jobs)

    # attach_parser = AttachCommand.add_parser(subparsers, completer=backend._completion_list_running_jobs)
    # stat_parser = StatCommand.add_parser(subparsers, completer=backend._completion_list_running_jobs)
    # test_parser = TestCommand.add_parser(subparsers)

    argcomplete.autocomplete(arg)
    args = arg.parse_args()

    if args.command == "run":
        operator = RunCommand()
        operator(
            config=args.config, image=args.image, entrypoint=args.entrypoint, namespace=args.namespace, name=args.name
        )
    elif args.command == "ls":
        operator = LsCommand()
        operator(namespace=args.namespace, show_all=args.all, head=args.top)
    elif args.command == "rm":
        operator = RmCommand()
        operator(job_name=args.job, namespace=args.namespace)
    elif args.command == "desc":
        operator = DescribeCommand()
        operator(job_name=args.job_name, namespace=args.namespace)
    elif args.command == "logs":
        operator = LogsCommand()
        operator(job_name=args.job, namespace=args.namespace, tail=args.tail, follow=args.follow)
    elif args.command == "attach":
        raise NotImplementedError  # TODO implement attach command
    elif args.command == "stat":
        raise NotImplementedError  # TODO implement stat command
    elif args.command == "test":
        raise NotImplementedError  # TODO implement test command -- run IB\scheduler\metrics\registry\ethernet tests
    else:
        arg.print_help()


if __name__ == "__main__":
    main()
