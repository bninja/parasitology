#!/usr/bin/env python
import argparse
import sys

import nsat


def nsat_cmd_parser(subparsers):
    nsat_parser = subparsers.add_parser('nsat')
    nsat_subparsers = nsat_parser.add_subparsers(title='techniques')

    parser = nsat_subparsers.add_parser('constraint')
    parser.set_defaults(cmd=nsat_contraint_cmd)

    parser = nsat_subparsers.add_parser('checksum')
    parser.add_argument('-j', '--parallel', action='store_true', default=False)
    parser.set_defaults(cmd=nsat_checksum_cmd)

    parser = nsat_subparsers.add_parser('checksum-http')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--path', default='/')
    parser.add_argument('-t', '--timeout', type=float, default=1.0)
    parser.add_argument('-j', '--parallel', action='store_true', default=False)
    parser.add_argument('-q', '--quiet', action='store_true', default=False)
    parser.set_defaults(cmd=nsat_checksum_http_cmd)


def nsat_contraint_cmd(args):
    for line in lines(args):
        expr = nsat.parse(line.strip())
        for ass in nsat.solve_constraint(expr):
            print ass


def nsat_checksum_cmd(args):
    match = nsat.checksums
    for line in lines(args):
        expr = nsat.parse(line.strip())
        for ass in nsat.solve_checksum(expr, match, args.parallel):
            print ass


def nsat_checksum_http_cmd(args):
    match = nsat.checksums_http(
        (args.host, args.port),
        path=args.path,
        timeout=args.timeout,
        verbose=not args.quiet,
    )
    for line in lines(args):
        expr = nsat.parse(line.strip())
        for ass in nsat.solve_checksum(expr, match, args.parallel):
            print ass


def cmd_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='commands')
    nsat_cmd_parser(subparsers)
    return parser


def lines(args):
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        yield line


def main():
    parser = cmd_parser()
    args = parser.parse_args()
    args.cmd(args)


if __name__ == '__main__':
    main()
