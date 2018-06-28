import logging
import sys


def init_loger(fn):
    logging.basicConfig(
        filename=fn,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        datefmt='%d-%m-%Y %H:%M:%S')
    logger = logging.getLogger()

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
