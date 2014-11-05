import threading
import wsgiref.simple_server

import iptc
import pytest

import nsat


nsat_fixtures = dict([
    # cnf
    ('!a and (b or c)', set([
        (('a', False), ('b', True), ('c', False)),
        (('a', False), ('b', True), ('c', True)),
        (('a', False), ('b', False), ('c', True)),

    ])),
    ('(a or b) and (!b or c or !d) and (d or !e)', set([
        (('a', False), ('b', True), ('c', True), ('d', True), ('e', False)),
        (('a', True), ('b', False), ('c', False), ('d', True), ('e', True)),
        (('a', True), ('b', False), ('c', True), ('d', False), ('e', False)),
        (('a', True), ('b', True), ('c', False), ('d', False), ('e', False)),
        (('a', True), ('b', False), ('c', False), ('d', False), ('e', False)),
        (('a', True), ('b', False), ('c', False), ('d', True), ('e', False)),
        (('a', False), ('b', True), ('c', False), ('d', False), ('e', False)),
        (('a', False), ('b', True), ('c', True), ('d', False), ('e', False)),
        (('a', False), ('b', True), ('c', True), ('d', True), ('e', True)),
        (('a', True), ('b', False), ('c', True), ('d', True), ('e', False)),
        (('a', True), ('b', True), ('c', True), ('d', True), ('e', True)),
        (('a', True), ('b', True), ('c', True), ('d', True), ('e', False)),
        (('a', True), ('b', False), ('c', True), ('d', True), ('e', True)),
        (('a', True), ('b', True), ('c', True), ('d', False), ('e', False)),
    ])),
    ('a or b', set([
        (('a', True), ('b', True)),
        (('a', True), ('b', False)),
        (('a', False), ('b', True)),
    ])),
    ('a and b', set([
        (('a', True), ('b', True)),
    ])),

    # non-cnf
    ('!(b or c)', set([
        (('b', False), ('c', False)),
    ])),
    ('(a and b) or c', set([
        (('a', True), ('b', False), ('c', True)),
        (('a', False), ('b', True), ('c', True)),
        (('a', False), ('b', False), ('c', True)),
        (('a', True), ('b', True), ('c', True)),
        (('a', True), ('b', True), ('c', False)),
    ])),
    ('a and (b or (d and e))', set([
        (('a', True), ('b', True), ('d', False), ('e', True)),
        (('a', True), ('b', False), ('d', True), ('e', True)),
        (('a', True), ('b', True), ('d', False), ('e', False)),
        (('a', True), ('b', True), ('d', True), ('e', False)),
        (('a', True), ('b', True), ('d', True), ('e', True)),
    ])),
])


def normalize(solns):
    return set(tuple(sorted(sol.items())) for sol in solns)


@pytest.fixture(scope='session')
def host(request):

    def app(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        ret = ['booyakasha\n']
        return ret

    def stop():
        server.shutdown()

    server = wsgiref.simple_server.make_server('127.0.0.1', 0, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    request.addfinalizer(stop)

    return server.server_address


@pytest.fixture(scope='session')
def ipt_rst_drop_rule(request, host):
    """
    tcp --tcp-flags RST RST -s {src} -d {dst} --dport {dst_port}
    """
    rule = iptc.Rule()
    rule.protocol = 'tcp'
    rule.src = '127.0.0.1'
    rule.dst = '127.0.0.1'

    match = iptc.Match(rule, 'tcp')
    match.dport = str(host[1])
    match.tcp_flags = ['RST', 'RST']
    rule.add_match(match)

    rule.target = iptc.Target(rule, 'DROP')

    table = iptc.Table(iptc.Table.FILTER)
    chain = iptc.Chain(table, 'OUTPUT')
    chain.insert_rule(rule, 0)

    def remove():
        chain.delete_rule(rule)

    request.addfinalizer(remove)


@pytest.mark.parametrize('raw', nsat_fixtures.keys())
def test_nsat_constraint(raw, ipt_rst_drop_rule):
    expr = nsat.parse(raw)
    expected = nsat_fixtures[raw]
    actual = normalize(nsat.solve_constraint(expr))
    assert expected == actual


@pytest.mark.parametrize('raw', nsat_fixtures.keys())
def test_nsat_checksum(raw):
    expr = nsat.parse(raw)
    expected = nsat_fixtures[raw]
    actual = normalize(nsat.solve_checksum(expr, nsat.checksums))
    assert expected == actual


@pytest.mark.parametrize('raw', [
    'a or b',
    'a and b',
    '!(b or c)',
])
def test_nsat_checksum_http(raw, host, ipt_rst_drop_rule):
    expr = nsat.parse(raw)
    expected = nsat_fixtures[raw]
    match = nsat.checksums_http(host)
    actual = normalize(nsat.solve_checksum(expr, match, parallel=True))
    assert expected == actual
