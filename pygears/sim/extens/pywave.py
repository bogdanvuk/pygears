import socket
import logging
import argparse
import sys
import os
import time
import pexpect.fdpexpect


# def send_cmd(sock, cmd, log_level='INFO', timeout=30):
def send_cmd(sock, cmd, log_level='INFO'):

    log_level = getattr(logging, log_level)

    errs = []
    ret = []

    try:
        # pexp = pexpect.fdpexpect.fdspawn(sock)
        # pexp.sendline(cmd)
        sock.send((cmd.replace('\n', '\r') + '\r').encode())

        if not cmd.startswith('exit'):
            data = ''
            while (1):
                data += sock.recv(4096).decode()

                if data.endswith('% '):
                    data = data.replace('% ', '')
                    break

            for line in data.strip().split('\n'):
                # for line in pexp.before.decode().split('\n'):
                if line.startswith('ERROR:') or line.startswith('WARNING:'):
                    errs.append(line)
                else:
                    ret.append(line)

    except socket.timeout as e:
        print('Command timeout', file=sys.stderr)
    except socket.error as e:
        print(e, file=sys.stderr)

    sock.close()
    return ret, errs


def connect_and_send(sock,
                     port,
                     log_level,
                     timeout,
                     cmd,
                     return_err=False,
                     check=False):
    sock.connect(('', port))
    sock.settimeout(timeout)

    if not check:
        # ret, errs = send_cmd(sock, cmd, log_level, timeout)
        ret, errs = send_cmd(sock, cmd, log_level)
        print('\n'.join(ret))
        print('\n'.join(errs), file=sys.stderr)
        if errs and return_err:
            return -1


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(prog="GTKWave deamon TCP server")

    parser.add_argument(
        '-p', dest='port', type=int, default=60000, help="Server port")

    parser.add_argument(
        '-c',
        dest='check',
        action='store_true',
        help="Only check if server is up")

    parser.add_argument(
        '-l', dest='log_level', default='INFO', help="Logging level")

    parser.add_argument(
        '-t', dest='timeout', type=int, default=30, help="Timeout")

    parser.add_argument('cmd', metavar='cmd', help="GTKWave TCL command")

    parser.add_argument(
        '-e', '--error', action='store_true', help="Return error")

    args = parser.parse_args(argv[1:])

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        return connect_and_send(client_socket, args.port, args.log_level,
                                args.timeout, args.cmd, args.error, args.check)
    except socket.error as err:
        if args.check:
            return -1

    command = [
        'python',
        os.path.join(os.path.dirname(__file__), 'pywave_server.py'),
        '-p',
        # f'{args.port}', '-l', f'{args.log_level}'
        f'{args.port}',
        '-l',
        'DEBUG'
    ]

    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.umask(0)
        os.execv(sys.executable, command)
    else:
        time.sleep(1)
        return connect_and_send(client_socket, args.port, args.log_level,
                                args.timeout, args.cmd, args.error)


if __name__ == '__main__':
    main(argv=[
        'pyvado', '-l', 'DEBUG', 'get_projects'
        # '{\nget_projects\nclose_projects\n}'
        # 'foreach {p} [get_projects] {\ncurrent_project p\n}'
        # 'version'
    ])
    # main()
