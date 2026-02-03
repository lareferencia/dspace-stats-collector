#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
from pathlib import Path
import re

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

version_file = Path("dspace_stats_collector/version.py").read_text(encoding="utf-8")
version_match = re.search(r'__version__\s*=\s*"([^"]+)"', version_file)
if version_match is None:
    raise RuntimeError("Could not find __version__ in dspace_stats_collector/version.py")
package_version = version_match.group(1)

requirements = [
    'requests',
    'pyjavaprops',
    'SQLAlchemy',
    'psycopg2-binary',
    'pysolr',
    'pandas',
    'urllib3',
    'pytz',
    'python-crontab',
    'anonymizeip',
    'pid',
    'tenacity',
]

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
            "dspace-stats-configure = dspace_stats_collector.configure:main",
            "dspace-stats-export = dspace_stats_collector.export:main"

        ]
}

setup(
    author="LA Referencia",
    author_email='soporte@lareferencia.redclara.net',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7',
    ],
    description="A python library for sending usage stats events from Dspace to Matomo",
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='dspace_stats_collector',
    name='dspace_stats_collector',
    packages=find_packages(include=['dspace_stats_collector*']),
    entry_points=entry_points,
 #   package_data=package_data,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/lareferencia/dspace-stats-collector',
    version=package_version,
    zip_safe=False,
)
