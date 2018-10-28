import os
import pkg_resources
import subprocess

os.environ['PYGEARS_VERSION'] = pkg_resources.get_distribution(
    "pygears").version

os.chdir('vagrant')
print('Deleting previous Vagrant VM')
subprocess.check_call('vagrant destroy -f', shell=True)
try:
    print('Starting Vagrant, log output to vagrant.log')
    ret = subprocess.check_call(
        'vagrant up > vagrant.log 2>&1', shell=True)
    print('[SUCCESS]')
    subprocess.check_call('vagrant destroy -f', shell=True)

except subprocess.CalledProcessError:
    print('[FAILED]')

os.chdir('..')
