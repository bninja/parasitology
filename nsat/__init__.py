import itertools
import multiprocessing
import struct

import constraint
from scapy import all as scapy

from .expression import var, and_, or_, not_, cnf, dnf, sat
from .grammar import parse
from . import spoof


__all__ = [
    'parse',
    'var',
    'and_',
    'or_',
    'not_',
    'cnf',
    'dnf',
    'sat',
    'spoof',
    'solve_bool',
    'solve_checksum',
    'checksums',
    'checksums_http',
]


def solve_constraint(expr):

    def _constraint(e):
        vars = [var.name for var in sub_e.vars]
        return lambda *vals: e.eval(dict(zip(vars, vals))), vars

    p = constraint.Problem()
    expr = cnf(expr)
    p.addVariables([var.name for var in expr.vars], [True, False])
    for _, sub_es in expr.traverse(depth=1):
        for sub_e in sub_es:
            p.addConstraint(*_constraint(sub_e))
    for solution in p.getSolutions():
        yield solution


def solve_checksum(expr, match=None, parallel=False):

    sat_expr = sat(expr)
    n = len(sat_expr.exprs[0])
    match = match or checksums

    def _checksums():
        if n == 2:
            g = itertools.product(*(
                [(0b01, 0b10)] * len(sat_expr) +
                [(0b00,)] * (8 - len(sat_expr))
            ))
        elif n == 3:
            g = itertools.product(*(
                [(0b01, 0b10, 0b11)] * len(sat_expr) +
                [(0b00,)] * (8 - len(sat_expr))
            ))
        for parts in g:
            checksum = 0
            for i, part in enumerate(parts):
                checksum |= part << (i * 2)
            yield checksum

    def _candidates():
        for vals in itertools.product(*([(True, False)] * len(sat_expr.vars))):
            yield dict(zip(sat_expr.vars, vals))

    def _bin(expr, assigment):
        val = assigment[expr.var]
        if isinstance(expr, not_):
            val = not val
        return 0b01 if val else 0b00

    def _assign(candidate):
        d = [0] * n
        for i, expr in enumerate(sat_expr):
            for j in range(n):
                d[j] |= _bin(expr[j], candidate) << (i * 2)
        return d

    def _debin(expr, assignment):
        val = assignment == 0b01
        return expr.var, (not val if isinstance(expr, not_) else val)

    def _assigment(d):
        assignment = set()
        for i, expr in enumerate(sat_expr):
            for j in range(n):
                assignment.add(_debin(expr[j], (d[j] >> (i * 2)) & 0b01))
        return dict(list(assignment))

    cases = itertools.izip(
        itertools.imap(_assign, _candidates()),
        itertools.repeat(list(_checksums()))
    )
    if parallel:
        pool = multiprocessing.Pool()
        matches = pool.imap(match, cases)
    else:
        matches = itertools.imap(match, cases)
    for data, soln in matches:
        if soln:
            yield dict(
                (var.name, val)
                for var, val in _assigment(data).iteritems()
            )


def checksums((data, checksums)):
    return data, any(sum(data) == checksum for checksum in checksums)


class _CheckSumHTTP(object):

    def __init__(self, host, path='/', retry=0, verbose=0, timeout=1.0):
        self.host = host
        self.path = path
        self.retry = retry
        self.verbose = verbose
        self.timeout = verbose

    def __call__(self, (data, checksums)):
        data_fmt = '!' + 'H' * len(data)
        for checksum in checksums:
            cxn = spoof.Connection(*self.host, verbose=self.verbose)
            with cxn.open():
                pkt = cxn.sendp(spoof.http_get_payload(
                    self.path,
                    data=struct.pack(
                        data_fmt, *([checksum] + [0] * (len(data) - 1))
                    ),
                ))
                c = type(pkt)(str(pkt))[scapy.TCP].chksum

                pkt = cxn.sendp(spoof.http_get_payload(
                    self.path,
                    data=struct.pack(data_fmt, *(data)),
                ))
                pkt[scapy.TCP].chksum = c
                count = 0
                while self.retry - count >= 0:
                    if cxn.send(pkt, timeout=self.timeout):
                        spoof.http_resp(cxn)
                        return data, True
                    count += 1
        return data, False


def checksums_http(host, path='/', retry=0, verbose=1, timeout=1.0):
    return _CheckSumHTTP(
        host, path=path, retry=retry, verbose=verbose, timeout=timeout,
    )
