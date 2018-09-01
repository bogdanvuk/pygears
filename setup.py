from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
import os
import glob


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
    version='0.2.3',
    description='Framework for hardware design ',

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
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    package_data={'': ['*.j2', '*.sv']},
    data_files=[
        ('pygears/cookbook/svlib', list(glob.iglob('pygears/cookbook/svlib/*.sv', recursive=True)))
    ],
    keywords='Gears System Design Python Simulator HDL ASIC FPGA',
    install_requires=['jinja2'],
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
