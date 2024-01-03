import argparse
from kubr.ls.operator import LSOperator

def main():
    arg = argparse.ArgumentParser(description='Kubr', add_help=True)
    arg.add_argument('--version', help='Get version of Kubr')
    subparsers = arg.add_subparsers(help='Commands', dest='command')

    submit_parser = subparsers.add_parser('run', help='Submit a new job')

    ls_parser = subparsers.add_parser('ls', help='List all jobs')
    ls_parser.add_argument('-n', '--namespace', help='Namespace to list jobs from', default='All')
    ls_parser.add_argument('-a', '--all', help='Show all jobs', action='store_true', default=False)
    ls_parser.add_argument('-t', '--top', help='Show only first T jobs', default=None, type=int)

    rm_parser = subparsers.add_parser('rm', help='Delete a job')
    rm_parser.add_argument('job', help='Name of job to delete')
    rm_parser.add_argument('-n', '--namespace', help='Namespace to delete job from', default='All')

    desc_parser = subparsers.add_parser('desc', help='Get info about a job')
    desc_parser.add_argument('job', help='Name of job to get info about')

    logs_parser = subparsers.add_parser('logs', help='Get logs of a job')
    logs_parser.add_argument('job', help='Name of job to get logs of')

    attach_parser = subparsers.add_parser('attach', help='Attach to a job')
    attach_parser.add_argument('job', help='Name of job to attach to')

    stat_parser = subparsers.add_parser('stat', help='Get stats of a cluster')

    args = arg.parse_args()

    if args.command == 'run':
        pass
    elif args.command == 'ls':
        operator = LSOperator()
        print(operator(namespace=args.namespace, show_all=args.all, head=args.top))
    elif args.command == 'rm':
        pass
    elif args.command == 'desc':
        pass
    elif args.command == 'logs':
        pass
    elif args.command == 'attach':
        pass
    else:
        arg.print_help()


if __name__ == '__main__':
    main()
