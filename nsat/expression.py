from __future__ import unicode_literals

import collections
import itertools
import random
import types


class Expression(object):

    def cnf(self):
        raise NotImplementedError

    def dnf(self):
        raise NotImplementedError

    def __unicode__(self):
        raise NotImplementedError

    def __str__(self):
        return self.__unicode__().encode('utf-8')

    def __invert__(self):
        return self.invert()

    def invert(self):
        raise NotImplementedError

    def traverse(self, depth=None):
        raise NotImplementedError

    def eval(self, assigments):
        raise NotImplementedError

    @property
    def var(self):
        vars = self.vars
        if len(vars) == 0:
            raise Exception('No vars')
        if len(vars) > 1:
            raise Exception('More than one var')
        return vars[0]

    @property
    def vars(self):
        return collections.OrderedDict(
            (e, None) for e, _ in self.traverse() if isinstance(e, Variable)
        ).keys()


class Variable(Expression):

    def __init__(self, name=None):
        super(Variable, self).__init__()
        name = name or self.generate_name()
        self.name = (
            name.decode('utf-8')
            if isinstance(name, basestring)
            else name
        )

    @classmethod
    def generate_name(cls):
        return 'g{0}'.format(random.getrandbits(32))

    def __cmp__(self, other):
        return self.name.__cmp__(other.name)

    def __eq__(self, other):
        return self.name.__eq__(other.name)

    def __hash__(self):
        return hash(self.name)

    # Expression

    def invert(self):
        return not_(self)

    def traverse(self, depth=None):
        yield self, []

    def eval(self, assigments):
        return assigments[self.name]

    def cnf(self):
        return self

    def dnf(self):
        return self

    def __unicode__(self):
        return self.name


class VectorOp(Expression):

    symbol = None

    def __init__(self, *exprs, **kwargs):
        super(VectorOp, self).__init__()
        if len(exprs) == 1:
            if isinstance(exprs[0], types.GeneratorType):
                exprs = exprs[0]
            elif isinstance(exprs[0], (list, tuple)):
                exprs = exprs[0]
        self.exprs = list(exprs)
        self.symbol = kwargs.pop('symbol', self.symbol)

    def __len__(self):
        return len(self.exprs)

    def __iter__(self):
        return iter(self.exprs)

    def __getitem__(self, index):
        return self.exprs[index]

    def collapse(self):
        es = []
        for e, sub_es in self.traverse():
            if not isinstance(e, type(self)):
                if isinstance(e, VectorOp):
                    e = e.collapse()
                es.append(e)
                del sub_es[:]
        return type(self)(es, symbol=self.symbol)

    # Expression

    def traverse(self, depth=None):
        sub_es = self.exprs[:]
        yield self, sub_es
        if depth is not None:
            depth -= 1
            if not depth:
                return
        for sub_e in sub_es:
            for n_e, n_sub_es in sub_e.traverse(depth):
                yield n_e, n_sub_es

    def __unicode__(self):

        def _parenthesize(e):
            return (
                (isinstance(e, VectorOp) and
                 not isinstance(e, type(self)) and
                 len(e) > 1)
            )

        return ' {op} '.format(op=self.symbol).join(
            '({0})'.format(e) if _parenthesize(e) else unicode(e)
            for e in self.exprs
        )


class And(VectorOp):

    # Expression

    def cnf(self):
        return and_(expr.cnf() for expr in self.exprs)

    def dnf(self):

        def _dnf(expr):
            dnf_e, dnf_es = self.l.dnf(), []
            for e, sub_es in dnf_e.traverse():
                if not isinstance(e, Or):
                    dnf_es.append(e)
                    del sub_es[:]
            return dnf_es

        return or_(
            and_(es)
            for es in itertools.product(*map(_dnf, self.exprs))
        )

    def invert(self):
        return or_(*map(not_, self.exprs))

    def eval(self, assigments):
        if len(self) == 1:
            return self.exprs[0].eval(assigments)
        return all(e.eval(assigments) for e in self.exprs)

    # VectorOp

    symbol = 'and'


class Or(VectorOp):

    # Expression

    def cnf(self):

        def _cnf(expr):
            cnf_e, cnf_es = expr.cnf(), []
            for e, sub_es in cnf_e.traverse():
                if not isinstance(e, And):
                    cnf_es.append(e)
                    del sub_es[:]
            return cnf_es

        return and_(
            or_(es)
            for es in itertools.product(*map(_cnf, self.exprs))
        )

    def dnf(self):
        return or_(expr.dnf() for expr in self.exprs)

    def invert(self):
        return and_(*map(not_, self.exprs))

    def eval(self, assigments):
        if len(self) == 1:
            return self.exprs[0].eval(assigments)
        return any(e.eval(assigments) for e in self.exprs)

    # VectorOp

    symbol = 'or'


class UnaryOp(Expression):

    symbol = None

    def __init__(self, expr, symbol=None):
        super(UnaryOp, self).__init__()
        self.expr = expr
        self.symbol = symbol or self.symbol

    def traverse(self, depth=None):
        sub_es = [self.expr]
        yield self, sub_es
        if depth is not None:
            depth -= 1
            if depth:
                return
        for sub_e in sub_es:
            for n_e, n_sub_es in sub_e.traverse(depth):
                yield n_e, n_sub_es


class Not(UnaryOp):

    # Expression

    def cnf(self):
        return self if isinstance(self.expr, Variable) else ~self.expr

    def dnf(self):
        return self if isinstance(self.expr, Variable) else ~self.expr

    def __unicode__(self):

        def _parenthesize(e):
            return isinstance(e, VectorOp) and len(e) > 1

        return '{0}{1}'.format(
            self.symbol,
            '({0})'.format(self.expr)
            if _parenthesize(self.expr)
            else self.expr
        )

    def invert(self):
        return self.e

    def eval(self, assigments):
        return not self.expr.eval(assigments)

    # UnaryOp

    symbol = '!'


and_ = And

or_ = Or

not_ = Not


def var(name=None):
    return Variable(name)


def cnf(expr):
    return expr.cnf()


def dnf(expr):
    return expr.dnf()


def sat(expr, n=None):

    def _2sat(cnf_expr):
        exprs = []
        for expr in cnf_expr:
            if len(expr.vars) > 2:
                raise ValueError('{0} has too many vars'.format(expr))
            if isinstance(expr, (Variable, UnaryOp)):
                expr = or_(expr, expr).collapse()
            elif isinstance(expr, Or):
                if len(expr) == 1:
                    expr = or_(expr, expr[0]).collapse()
                elif len(expr) == 2:
                    pass
                else:
                    raise ValueError('{0} has too many expressions'.format(expr))
            else:
                raise ValueError('{0} invalid'.format(expr))
            exprs.append(expr)
        return and_(exprs)

    def _3sat(cnf_expr):
        exprs = []
        for expr in cnf_expr:
            if isinstance(expr, (Variable, UnaryOp)):
                expr = or_(expr, expr, expr).collapse()
            elif isinstance(expr, Or):
                if len(expr) == 1:
                    expr = or_(expr, expr[0], expr[0]).collapse()
                elif len(expr) == 2:
                    expr = Or(expr, expr[0]).collapse()
                elif len(expr) == 3:
                    pass
                else:
                    es, le = [], None
                    for i in range(0, len(expr), 2):
                        se = expr[i:i + 2]
                        if le is None:
                            if i + 2 >= len(expr):
                                se.extend([se[0]] * (3 - len(se)))
                            else:
                                le = var()
                                se.append(le)
                        else:
                            se = [not_(le)] + se
                            le = None
                            if len(se) < 3:
                                se.extend([se[-1]] * (3 - len(se)))
                        es.append(or_(se))
                    expr = and_(es)
            else:
                raise ValueError('{0} invalid'.format(expr))
            exprs.append(expr)
        return and_(exprs)

    cnf_expr = cnf(expr).collapse()
    if n is None:
        n = 2 if max(len(clause.vars) for clause in cnf_expr) < 3 else 3
    if n == 2:
        sat_expr = _2sat(cnf_expr)
    elif n == 3:
        sat_expr = _3sat(cnf_expr)
    else:
        raise ValueError('n={0} invalid'.format(n))
    return sat_expr
