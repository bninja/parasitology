from ply import lex, yacc

from . import var, and_, or_, not_


def parse(data):
    return yacc.parse(data)


# tokens

reserved = {
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
}

tokens = [
    'VAR', 'LPAREN', 'RPAREN', 'AND', 'OR', 'NOT',
]

t_LPAREN = r'\('

t_RPAREN = r'\)'

t_AND = r'\&{1,2}'

t_OR = r'\|{1,2}'

t_NOT = r'\!|\~'

t_ignore = ' \t'


def t_VAR(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'VAR')
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')


def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


lex.lex()


# rules

precedence = (
    ('left', 'AND', 'OR'),
    ('right', 'NOT'),
)


def p_expression_var(t):
    '''
    expression : VAR
    '''
    t[0] = var(t[1])


def p_expression_group(t):
    '''
    expression : LPAREN expression RPAREN
    '''
    t[0] = t[2]


def p_expression_uop(t):
    '''
    expression : NOT expression
    '''
    t[0] = not_(t[2])


def p_expression_bop(t):
    '''
    expression : expression AND expression
               | expression OR expression
    '''
    if t[2] in ('and', '&&', '&'):
        t[0] = and_(t[1], t[3], symbol=t[2])
    elif t[2] in ('or', '||', '|'):
        t[0] = or_(t[1], t[3], symbol=t[2])


def p_error(t):
    print("Syntax error at '%s'" % t.value)


yacc.yacc(debug=0, write_tables=0)
