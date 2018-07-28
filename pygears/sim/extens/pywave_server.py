#!/usr/bin/env python3

import contextlib
import select
import socket
import pexpect
import logging
import argparse
import os
import re
import sys


def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=1, max_fails=3):
    """Set TCP keepalive on an open socket.

    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


def client_loop(client, p):
    while 1:
        data_sent = None
        ready = select.select([client], [], [], 0.01)

        if ready[0]:
            try:
                data_sent = client.recv(4096)
                if data_sent:
                    data_sent = data_sent.decode()
                    logging.debug(f'Received client data: {data_sent}')
                    p.send(data_sent)
                else:
                    logging.info(
                        f'EOF received at client socket {client.fileno()}')
                    return
            except ConnectionResetError:
                return

        data = ''
        iters = 0
        try:
            while (1):
                data += p.read_nonblocking(
                    size=4096, timeout=0.01 if (data_sent is None) else 0.1)
                iters += 1

        except pexpect.TIMEOUT:
            if data:
                lines = data.split('\r\n')
                for i in range(len(lines)):
                    if lines[0].endswith("% "):
                        break
                else:
                    i = 0
                data = '\n'.join(lines[i:])
                if data_sent:
                    data = data.replace(data_sent.replace('\r', '\n'), '')
                logging.debug(f'Sending to client: {repr(data)}')
                client.sendall(data.encode())
        except Exception as e:
            logging.exception("Pexpect exception")
            raise


def open_socket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    sock.listen(1)
    set_keepalive_linux(sock)

    return sock


def server_loop(port, log_level='INFO'):
    logging.basicConfig(
        filename=os.path.expanduser(f'~/pywave_{port}.log'),
        level=getattr(logging, log_level),
        format='%(asctime)s %(levelname)-8s %(message)s')

    logging.info(f'Pywave process started, pid={os.getpid()}')

    try:
        sock = open_socket(port)
    except socket.error as err:
        logging.exception("Socket error")
        raise

    logging.info(f'Server socket {sock.fileno()} opened at port {port}.')

    try:

        p = pexpect.spawnu('gtkwave -W')
        p.expect('%')
        version = re.search(r"GTKWave Analyzer v(\d{1}\.\d{1}.\d{2})",
                            p.before).group(0)

        logging.info(f'GTKWave {version} started, listening on port {port}...')

        while 1:
            client, address = sock.accept()
            logging.info(f'Client connected at socket {client.fileno()}')
            client.setblocking(0)

            try:
                client_loop(client, p)
            except pexpect.EOF:
                logging.info('GTKWave terminated unexpectedly. Exiting...')
                return
            except Exception:
                raise
            finally:
                logging.info(
                    f'Client at socket {client.fileno()} disconnected.')
                client.close()

    except Exception:
        sock.close()
        # p.terminate()
        raise


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(prog="GTKWave deamon TCP server")

    parser.add_argument(
        '-p', dest='port', type=int, default=60000, help="Server port")

    parser.add_argument(
        '-l', dest='log_level', default='INFO', help="Logging level")

    args = parser.parse_args()

    with open(os.path.expanduser(f'~/pywave_{args.port}.stdout'), 'w') as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            server_loop(args.port, args.log_level)


if __name__ == '__main__':
    main()
