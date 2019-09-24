import os
import logging
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection
from functools import partial
from traceback import extract_tb, format_list
from pygears.conf import inject, Inject


def finish():
    os.system(f'pywave "exit"')


def pywave_running():
    return not os.system('pywave -c ""')


def pywave_reload():
    os.system(f'pywave "gtkwave::reLoadFile"')


def pywave_load_file(fn):
    if os.path.isfile(fn):
        os.system(f'pywave "gtkwave::loadFile {fn}"')


def ActivityWaveFactory(cfg):
    class ActivityWave(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super(ActivityWave, self).__init__(*args, **kwargs)

        def log_request(code='-', size='-'):
            pass

        def log_error(fmt, *args):
            pass

        def log_message(fmt, *args):
            pass

        def do_GET(self):
            """Respond to a GET request."""

            logging.info(f'Request received: {self.path}')

            try:
                self.send_response(200)
                if not self.path:
                    logging.info(f'Here?')
                    return
                elif self.path[0] == ':':
                    logging.info(f'Filedir received: {self.path}')
                    running = pywave_running()
                    if ('filedir' in cfg and cfg['filedir'] == self.path[1:]
                            and running):
                        pywave_reload()
                    else:
                        cfg['filedir'] = self.path[1:]
                        if running:
                            finish()

                        pywave_load_file(f"{cfg['filedir']}/pygears.vcd")
                        pywave_load_file(f"{cfg['filedir']}/issue.sav")

                elif self.path[0] == '/':
                    gear = self.path[1:]
                    if 'filedir' in cfg:
                        logging.info(f'Gear received: {self.path}')
                        pywave_load_file(f"{cfg['filedir']}/{gear}.sav")

                    logging.info(f'Here 0')
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        f"<html><head><title>{gear}.</title></head>".encode())

                    if 'filedir' in cfg:
                        self.wfile.write(
                            f"<body><p>Reading from: {cfg['filedir']}.</p>".
                            encode())

                    self.wfile.write(b"<p>")

                    fn = f"{cfg['filedir']}/{gear}.txt"
                    if os.path.isfile(fn):
                        with open(fn, 'r') as f:
                            for line in f:
                                self.wfile.write(f'{line}<br/>'.encode())

                    self.wfile.write(b"</p></body></html>")

            except Exception as e:
                type, value, tr = sys.exc_info()
                for s in format_list(extract_tb(tr)):
                    logging.info(s)

                logging.info(f'Error: {e}')

                raise e

    return ActivityWave


def restart_wave(sim, outdir, address):

    # conn = HTTPConnection(f'http://{address[0]}:{address[1]}')
    # conn.request('HEAD', f'http://{address[0]}:{address[1]}:{outdir}')
    # return

    while True:
        try:
            time.sleep(1)
            conn = HTTPConnection(f'{address[0]}:{address[1]}')
            conn.request('GET', f':{outdir}')
            return
        except ConnectionRefusedError:
            # print("Fail!")
            # raise e
            # return
            conn.close()
            command = [
                'python',
                os.path.join(os.path.dirname(__file__), 'activity_wave.py')
            ]

            pid = os.fork()
            if pid == 0:
                os.setsid()
                os.umask(0)
                os.execv(sys.executable, command)
            else:
                pass


@inject
def activity_wave(top,
                  sim=Inject('sim/simulator'),
                  outdir=Inject('results-dir')):
    outdir = os.path.abspath(outdir)
    sim.events['at_exit'].append(
        partial(restart_wave, outdir=outdir, address=('localhost', 5000)))


def run(address=('', 5000), server_class=HTTPServer):
    cfg = {'address': address}

    logging.basicConfig(
        filename=os.path.expanduser(f'~/activity_wave_{address[1]}.log'),
        level=getattr(logging, 'INFO'),
        format='%(asctime)s %(levelname)-8s %(message)s')

    logging.info(f'ActivityWave process started, pid={os.getpid()}')
    httpd = server_class(address, ActivityWaveFactory(cfg))
    httpd.serve_forever()


if __name__ == "__main__":
    run()
