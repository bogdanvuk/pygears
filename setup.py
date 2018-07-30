from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
import os


def setup_home():
    os.makedirs(os.path.expanduser('~/.pygears'), exist_ok=True)
    os.makedirs(os.path.expanduser('~/.pygears/svlib'), exist_ok=True)


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        setup_home()


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        setup_home()


setup(
    name='pygears',
    version='0.1',
    description=
    'Tools for the Gears HDM (Hardware Design Methodology) written in Python',

    # The project's main homepage.
    url='https://github.com/bogdanvuk/pygears.git',

    # Author details
    author='Bogdan Vukobratovic',
    author_email='bogdan.vukobratovic@gmail.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Gears System Design Python Simulator HDL ASIC FPGA',
    packages=find_packages(exclude=['examples*', 'docs', 'svlib']),
    entry_points={
        'console_scripts': [
            'pywave = pygears.sim.extens.pywave:main',
        ],
    },
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
)
