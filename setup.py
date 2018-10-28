from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.egg_info import egg_info
import os
import glob


def setup_home():
    os.makedirs(os.path.expanduser('~/.pygears'), exist_ok=True)
    os.makedirs(os.path.expanduser('~/.pygears/svlib'), exist_ok=True)


class PostEggInfoCommand(egg_info):
    def run(self):
        egg_info.run(self)
        setup_home()


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


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='pygears',
    version='0.1.2',
    description='Framework for functional hardware design approach',
    long_description=readme(),
    url='https://www.pygears.org',
    # download_url = '',

    author='Bogdan Vukobratovic',
    author_email='bogdan.vukobratovic@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    python_requires='>=3.6.0',
    package_data={'': ['*.j2', '*.sv']},
    include_package_data=True,
    keywords='functional hardware design Python simulator HDL ASIC FPGA Gears',
    install_requires=['jinja2>=2.10', 'pygears-tools'],
    packages=find_packages(exclude=['examples*', 'docs']),
    entry_points={
        'console_scripts': [
            'pywave = pygears.sim.extens.pywave:main',
        ],
    },
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
        'egg_info': PostEggInfoCommand,
    },
)
