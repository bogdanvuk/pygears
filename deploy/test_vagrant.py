import os
import pkg_resources
import subprocess
import logging


def create_logger(os_name):
    logger = logging.getLogger(os_name)
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s [%(name)-12s]: %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


os.environ['PYGEARS_VERSION'] = pkg_resources.get_distribution(
    "pygears").version

os.chdir('vagrant')

for f in os.listdir():
    if f not in ['common'] and os.path.isdir(f):
        logger = create_logger(f)
        os.chdir(f)
        logger.info('Deleting previous Vagrant VM')
        subprocess.check_call('vagrant destroy -f', shell=True)
        try:
            logger.info('Starting Vagrant, log output to vagrant.log')
            ret = subprocess.check_call(
                'vagrant up > vagrant.log 2>&1', shell=True)
            logger.info('[SUCCESS]')
            subprocess.check_call('vagrant destroy -f', shell=True)

        except subprocess.CalledProcessError:
            logger.info('[FAILED]')

        os.chdir('..')
