#!/usr/bin/env python
# coding=utf-8

import os
import sys

from setuptools import setup, find_packages

if not hasattr(sys, 'version_info') or sys.version_info < (2, 6, 0, 'final'):
	sys.exit('d2l_thrive requires Python 2.6 or later.')

setup(
	name = 'd2l_thrive',
	version = '0.1',

	author = 'Derrick Woo',
	author_email = 'dpywoo@ucalgary.ca',
	description = 'Processing scripts to support D2L to Thrive data feeds.',

	packages = find_packages(),
	install_requires = [
		'CouchDB>=0.9',
		'python_daemon>=1.6',
		'argparse>=1.1',
		'requests>=2.2.1',
		'unicodecsv>=0.9.4',
		'progressbar>=2.2'
	],

	entry_points = {
		'console_scripts': [
			'import-thrive-items = d2l_thrive.import:main'
		]
	},

	zip_safe = True
)
