#!/usr/bin/env python

import argparse
import logging
import threading
import wsgiref.simple_server


def app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    ret = ['booyakasha\n']
    return ret


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('port_start', nargs=1, type=int)
    parser.add_argument('port_end', nargs='?', type=int)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--poll', type=float, default=1.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    ports = range(
        args.port_start[0],
        args.port_end if args.port_end else args.port_start[0] + 1,
        1,
    )
    threads = []
    for server in [
            wsgiref.simple_server.make_server(args.host, port, app)
            for port in ports
            ]:
        logging.info('hosting %s:%s', *server.server_address)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    while threads:
        threads[-1].join(args.poll)
        if not threads[-1].is_alive:
            threads.pop()


if __name__ == '__main__':
    main()
