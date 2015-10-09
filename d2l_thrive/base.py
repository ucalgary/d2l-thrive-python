#!/usr/bin/env python
# coding=utf-8

import os
import sys

from couchdb.client import Database
from couchdb.http import ResourceNotFound, ResourceConflict


class BaseObject(object):

	def __init__(self, args=None):
		self._args = args or sys.argv[1:]

	def run(self):
		"""The main runloop. Scripts should call this method
		after instantiating an object."""

		parser = self.argument_parser()
		self.args = parser.parse_args(self._args)
		self.unpack_arguments(self.args)

		# Give subclasses an opportunity to perform additional setup functions
		# before main is invoked.
		self.prepare_for_main()

		if not self.args.background:
			result = self.main()
		else:
			import daemon
			import grp
			import pwd
			import signal
			from lockfile.pidlockfile import PIDLockFile
			
			# Create and configure the daemon context
			ctx = daemon.DaemonContext()
			ctx.umask = 0o027
			ctx.pidfile = PIDLockFile(self.args.pidfile)
			# ctx.signal_map = {
			# 	signal.SIGTERM: # program_cleanup,
			# 	signal.SIGUP: 'terminate',
			# 	signal.SIGUSR1: # reload_program_config
			# }
			ctx.uid = pwd.getpwnam('nobody').pw_uid
			ctx.gid = grp.getgrnam('nobody').gr_gid
			
			# Daemonize by running within the daemon context
			with ctx:
				result = self.main()

		# Exit with the code returned from main.
		sys.exit(result)

	# Configuring the observer
			
	def argument_parser(self):
		import argparse
	
		parser = argparse.ArgumentParser()
		
		parser.add_argument('-b', '--background', help='run as a background process', default=False, action='store_true')
		parser.add_argument('-p', '--pidfile', help='set the background PID FILE', default='/var/run/%s.pid' % self.__class__.__name__)

		return parser

	def unpack_arguments(self, args):
		pass

	def prepare_for_main(self):
		"""A stub method for library classes to optionally implement. Typically,
		this is only used by classes that expect to be subclassed for actual use and
		wish to perform some functions at the start of main, without implementing
		main so that further subclasses can implement main to perform their actual
		work. Subclasses should call super on this function if it is implemented.
		"""
		pass
		
	def main(self):
		"""A stub method for subclasses to implement. Subclasses should override
		``main`` to perform their specific functions.
		"""
		pass


class LMSObject(BaseObject):

	def __init__(self, args=None, connection_info=None):
		super(LMSObject, self).__init__(args=args)

	def couchdb_client(self, name):
		return self._named_client(name, self.create_couchdb_client)
		
	def _named_client(self, name, create_f):
		key_prefix = name + '_'
		info_keys = [key for key in os.environ.keys() if key.startswith(key_prefix)]
		if len(info_keys) == 0:
			return None
			
		# Dictionary comprehension replaced for Python 2.6 compatibility
		# info = { key[len(key_prefix):]: os.environ[key] for key in info_keys }
		info = dict((key[len(key_prefix):], os.environ[key]) for key in info_keys)
			
		if 'URL' in info:
			url = info['URL']
		elif 'RESOURCE' in info:
			import pkg_resources
		
			path = pkg_resources.resource_filename('adsm', info['RESOURCE'])
			url = 'file://%s' % path
			
		args = info.get('args', {})
		
		return create_f(url, **args)

	def create_couchdb_client(self, db_url, require_exists=True, **args):
		db = Database(db_url)
		
		if require_exists:
			try:
				db.info()
			except ResourceNotFound:
				raise Exception('No database found at %s' % db.resource.url)
		
		return db

