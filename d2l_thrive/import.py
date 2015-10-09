#!/usr/bin/env python
# coding=utf-8

import hashlib
import itertools
import os
import progressbar
import sys

import unicodecsv

from .base import LMSObject


class D2LThriveReportImporter(LMSObject):

	def argument_parser(self):
		parser = super(D2LThriveReportImporter, self).argument_parser()

		parser.add_argument('report_file', help='Path to CSV report file generated by Desire2Learn')
		parser.add_argument('thrive_db_name', default='THRIVE_DB', nargs='?', help='Environment variable name for course items database info')
		parser.add_argument('batch_size', default=2000, type=int, nargs='?', help='Batch size for CouchDB bulk document requests')

		return parser

	def prepare_for_main(self):
		self.thrive_db = self.couchdb_client(self.args.thrive_db_name)
		self._items_to_process = []
		self._items_to_post = []

	def main(self):
		with open(self.args.report_file, 'r') as report_file:
			progress = progressbar.ProgressBar(maxval=os.path.getsize(self.args.report_file))
			progress.start()

			report_reader = unicodecsv.DictReader(report_file, delimiter=',', quotechar='"')
			for report_item in report_reader:
				progress.update(report_file.tell())
				
				# Generate a document id for the item. The id consists of the course's
				# OrgUnitID and a hash of the URL.
				#url_digest = hashlib.sha1(report_item['URL'].encode('utf-8')).hexdigest()
				doc_id = '%s-%s' % (report_item['Course Offering Code'], report_item['Grade Item Id'])
				report_item['_id'] = doc_id

				self.process_item(report_item)

			self.finalize_items()
			progress.finish()

	def process_item(self, item, now=False):
		self._items_to_process.append(item)

		if len(self._items_to_process) >= self.args.batch_size:
			self.process_items()

	def process_items(self):
		if len(self._items_to_process) == 0:
			return

		# Determine which queued items already exist in the database.
		all_item_ids = [item['_id'] for item in self._items_to_process]
		fetch_result = self.thrive_db.view('_all_docs', keys=all_item_ids)

		# For each item and fetch result combo, post the item if
		# it is not found in the database.
		assert len(fetch_result) == len(self._items_to_process)
		for item, result in itertools.izip(self._items_to_process, fetch_result):
			if result.get('error') == 'not_found':
				self.prepare_item_for_posting(item)
				self.post_item(item)

		# Throw away the list of items to process. Non-existent items should
		# now be in the _items_to_post list or already posted. Items that
		# already existed are currently ignored.
		self._items_to_process = []

	def prepare_item_for_posting(self, item):
		# Convert empty field values to None
		for k, v in item.iteritems():
			if v == '':
				item[k] = None

	def post_item(self, item, now=False):
		self._items_to_post.append(item)

		if len(self._items_to_post) >= self.args.batch_size:
			self.post_items()

	def post_items(self):
		if len(self._items_to_post) == 0:
			return

		# Do a bulk document update to save the items in the database.
		self.thrive_db.update(self._items_to_post)

		# Throw away the list of items to save. The items should now be
		# in the database
		# assert all((item['_id'] in self.thrive_db for item in self._items_to_post))
		self._items_to_post = []

	def finalize_items(self):
		self.process_items()
		self.post_items()


def main(args=None):
	return D2LThriveReportImporter(args=args).run()


if __name__ == '__main__':
	main()