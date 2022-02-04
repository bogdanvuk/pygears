from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.egg_info import egg_info
import os


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


this_directory = os.path.abspath(os.path.dirname(__file__))


def readme():
    with open(os.path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
        return f.read()


# TODO: Make it work for new jinja versions

setup(
    name='pygears',
    version='0.3.3',
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
        'Programming Language :: Python :: 3.7',
    ],
    python_requires='>=3.6.0',
    package_data={'': ['*.j2', '*.v', '*.sv', '*.svt', '*.vt']},
    include_package_data=True,
    keywords='functional hardware design Python simulator HDL ASIC FPGA Gears',
    install_requires=[
        'jinja2', 'dataclasses;python_version<"3.7"', 'pyvcd', 'attrs', 'stopit'
    ],
    setup_requires=[
        'jinja2', 'dataclasses;python_version<"3.7"', 'pyvcd', 'attrs', 'stopit'
    ],
    packages=find_packages(exclude=['examples*', 'docs']),
    extras_require={'pytest': ['pytest', 'pytest-xdist', 'filelock']},
    entry_points={
        'console_scripts': [
            'pygears = pygears.entry:main',
        ],
        'pytest11': ['pytest_pygears = pygears.util.pytest_pygears']
    },
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
        'egg_info': PostEggInfoCommand,
    },
)
