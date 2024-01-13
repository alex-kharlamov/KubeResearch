# PYTHON_ARGCOMPLETE_OK
import argcomplete, argparse

from kubr.logs.operator import LOGSOperator
from kubr.ls.operator import LSOperator
from kubr.rm.operator import RMOperator
from kubr.run.operator import RUNOperator


def main():
    arg = argparse.ArgumentParser(description='Kubr', add_help=True)
    arg.add_argument('--version', help='Get version of Kubr')
    subparsers = arg.add_subparsers(help='Commands', dest='command')

    run_parser = subparsers.add_parser('run', help='Submit a new job')
    run_parser.add_argument('config',  help='Path to run config', type=str)
    # run_parser.add_argument('-i', '--image', help='Image to run')
    # run_parser.add_argument('-e', '--entrypoint', help='Entrypoint to run')
    # run_parser.add_argument('-a', '--args', help='Arguments to pass to command')
    # run_parser.add_argument('-e', '--env', help='Environment variables to pass to command')
    # run_parser.add_argument('-r', '--resources', help='Resources to request')
    # run_parser.add_argument('-l', '--labels', help='Labels to add to job')
    # run_parser.add_argument('-n', '--namespace', help='Namespace to submit job to', default='default')

    ls_parser = subparsers.add_parser('ls', help='List all jobs')
    ls_parser.add_argument('-n', '--namespace', help='Namespace to list jobs from', default='All')
    ls_parser.add_argument('-a', '--all', help='Show all jobs', action='store_true', default=False)
    ls_parser.add_argument('-t', '--top', help='Show only first T jobs', default=None, type=int)

    rm_parser = subparsers.add_parser('rm', help='Delete a job')
    rm_parser.add_argument('job', help='Name of job to delete')
    rm_parser.add_argument('-n', '--namespace', help='Namespace to delete job from', default='default')

    desc_parser = subparsers.add_parser('desc', help='Get info about a job')
    desc_parser.add_argument('job', help='Name of job to get info about')

    logs_parser = subparsers.add_parser('logs', help='Get logs of a job')
    logs_parser.add_argument('job', help='Name of job to get logs of')
    logs_parser.add_argument('-n', '--namespace', help='Namespace to get logs from', default='default')
    logs_parser.add_argument('-t', '--tail', help='Number of lines to show', default=10, type=int)

    attach_parser = subparsers.add_parser('attach', help='Attach to a job')
    attach_parser.add_argument('job', help='Name of job to attach to')

    stat_parser = subparsers.add_parser('stat', help='Get stats of a cluster')

    argcomplete.autocomplete(arg)
    args = arg.parse_args()

    if args.command == 'run':
        operator = RUNOperator()
        print(operator(config=args.config))
    elif args.command == 'ls':
        operator = LSOperator()
        print(operator(namespace=args.namespace, show_all=args.all, head=args.top))
    elif args.command == 'rm':
        operator = RMOperator()
        print(operator(job_name=args.job, namespace=args.namespace))
    elif args.command == 'desc':
        raise NotImplementedError  # TODO implement desc command
    elif args.command == 'logs':
        operator = LOGSOperator()
        print(operator(job_name=args.job, namespace=args.namespace, tail=args.tail))
    elif args.command == 'attach':
        raise NotImplementedError   # TODO implement attach command
    elif args.command == 'stat':
        raise NotImplementedError  # TODO implement stat command
    elif args.command == 'test':
        raise NotImplementedError  # TODO implement test command -- run IB\scheduler\metrics\registry\ethernet tests
    else:
        arg.print_help()


if __name__ == '__main__':
    main()
