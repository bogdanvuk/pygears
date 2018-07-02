from setuptools import setup, find_packages

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
)
