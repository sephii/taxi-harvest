#!/usr/bin/env python
from setuptools import find_packages, setup
from taxi_harvest import __version__


install_requires = [
    'requests>=2.3.0',
    'python-slugify>=1.1.3',
    'arrow>=0.6.0',
]

setup(
    name='taxi_harvest',
    version=__version__,
    packages=find_packages(),
    description='Harvest backend for Taxi',
    author='Sylvain Fankhauser',
    author_email='sylvain.fankhauser@liip.ch',
    url='https://github.com/sephii/taxi-harvest',
    install_requires=install_requires,
    license='wtfpl',
    entry_points={
        'taxi.backends': 'harvest = taxi_harvest.backend:HarvestBackend'
    }
)
