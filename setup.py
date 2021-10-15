#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

#with open('requirements.txt') as required_file:
#    requirements = required_file.read().splitlines()

requirements = []

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

#package_data={
        # And include any found in the 'config' subdirectory
#        'config': ['config/*.*'],
#}

entry_points={
        'console_scripts': [
            "dspace-stats-collector = dspace_stats_collector.collector:main",
            "dspace-stats-cronify = dspace_stats_collector.croninstaller:main",
            "dspace-stats-configure = dspace_stats_collector.configure:main"

        ]
}

setup(
    author="LA Referencia",
    author_email='lareferencia.dev@gmail.com',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="A python library for sending usage stats events from Dspace to Matomo & ELK",
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='dspace_stats_collector',
    name='dspace_stats_collector',
    packages=find_packages(include=['dspace_stats_collector']),
    entry_points=entry_points,
 #   package_data=package_data,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/lareferencia/dspace-stats-collector',
    version='0.5.5',
    zip_safe=False,
)
