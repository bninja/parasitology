import contextlib
import httplib
import StringIO
import time

from scapy import all as scapy


class Connection(object):

    def __init__(self, host, port, verbose=0):
        self.sock = None
        self.dst = host
        self.dport = port
        self.sport = None
        self.rseq = None
        self.wseq = None
        self.verbose = verbose

    def open(self):
        self.sock = scapy.L3RawSocket()
        try:
            # syn
            tcp = scapy.TCP(
                dport=self.dport,
                sport=scapy.RandShort(),
                flags='S',
            )
            p = self.sock.sr1(
                scapy.IP(dst=self.dst) / tcp,
                verbose=self.verbose,
            )
            self.sport = p[scapy.TCP].dport
            self.wseq = p[scapy.TCP].ack
            self.rseq = p[scapy.TCP].seq

            # ack
            tcp = scapy.TCP(
                dport=self.dport,
                sport=self.sport,
                seq=self.wseq,
                ack=self.rseq + 1,
                flags='A',
            )
            self.sock.send(scapy.IP(dst=self.dst) / tcp)
        except:
            self.sock.close()
            self.sock = None
            raise

        @contextlib.contextmanager
        def _close():
            try:
                yield
            finally:
                self.close()

        return _close()

    def sendp(self, payload):
        tcp = scapy.TCP(
            dport=self.dport,
            sport=self.sport,
            seq=self.wseq,
            flags='P',
        )
        return scapy.IP(dst=self.dst) / tcp / payload

    def send(self, p, timeout=None):
        if not isinstance(p, scapy.Packet):
            p = self.sendp(p)
        r = self.sock.sr1(p, timeout=timeout, verbose=self.verbose)
        if not r:
            return False
        self.wseq += len(p[scapy.TCP].payload)
        return True

    def recv(self, n=None, timeout=None):

        def lfilter(p):
            return (
                p.haslayer(scapy.IP) and
                p[scapy.IP].dst == self.dst and
                p.haslayer(scapy.TCP) and
                p[scapy.TCP].sport == self.dport and
                p[scapy.TCP].dport == self.sport and
                p[scapy.TCP].seq not in seqs
            )

        def prn(p):
            seqs.append(p[scapy.TCP].seq)
            lens.append(len(p[scapy.TCP].payload))

        def stop_filter(p):
            return (
                (expires_at and expires_at < time.time()) or
                (n and sum(lens) >= n) or
                (p[scapy.TCP].flags & 1 == 1)
            )

        seqs, lens, expires_at = (
            [],
            [],
            time.time() + timeout if timeout else None,
        )

        # recv
        ps = self.sock.sniff(
            lfilter=lfilter,
            prn=prn,
            stop_filter=stop_filter,
            timeout=timeout,
            verbose=self.verbose,
        )

        payload = ''.join(
            str(p[scapy.TCP].payload or '') for p in ps
        )

        # ack
        rseq = ps[-1][scapy.TCP].seq + len(str(ps[-1][scapy.TCP].payload) or '')
        tcp = scapy.TCP(
            dport=self.dport,
            sport=self.sport,
            flags='A',
            seq=self.wseq,
            ack=rseq + 1,
        )
        self.sock.send(scapy.IP(dst=self.dst) / tcp)
        self.rseq = rseq

        # closed?
        if ps[-1][scapy.TCP].flags & 1:
            self.sock.close()
            self.sock = None

        return payload

    def close(self):
        if not self.sock:
            return
        try:
            # fin
            tcp = scapy.TCP(
                dport=self.dport,
                sport=self.sport,
                seq=self.wseq,
                flags='F'
            )
            r = self.sock.sr1(
                scapy.IP(dst=self.dst) / tcp,
                verbose=self.verbose,
            )
            self.wseq = r[scapy.TCP].ack

            # ack
            tcp = scapy.TCP(
                dport=self.dport,
                sport=self.sport,
                flags='A',
                seq=self.wseq,
                ack=r[scapy.TCP].seq + 1,
            )
            self.sock.send(scapy.IP(dst=self.dst) / tcp)
            self.rseq = r[scapy.TCP].seq
        finally:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None


def http_get_payload(path, headers=None, data=None):
    headers = headers or {}
    reql = [
        'GET {0} HTTP/1.0'.format(path).encode('utf-8')
    ] + [
        '{0}: {1}'.encode('utf-8').format(k, v) for k, v in headers.iteritems()
    ]
    if data:
        if isinstance(data, unicode):
            data = data.encode('utf-8')
    else:
        data = b''
    reql.extend([data, b''])
    return b'\r\n'.join(reql)


def http_resp(cxn):

    class _DummySocket(object):

        def __init__(self, raw):
            self.raw = raw

        def makefile(self, *args, **kwargs):
            return StringIO.StringIO(self.raw)

    resp = cxn.recv()
    respw = httplib.HTTPResponse(_DummySocket(resp))
    respw.begin()
    return respw


def http_get(cxn, path, headers=None, data=None):
    p = cxn.sendp(http_get_payload(path, headers, data))
    cxn.send(p)
    return http_resp(cxn)
