# Mbf, the mud bot framework - utilities
# Author: Blake Oliver <oliver22213@me.com>

import re

def match_regexp_list(r_list, string):
	"""Given a list of regular expressions and a string to match them all against, return a list of tuples of (regexp, match object). If there were no matches, return false.
	"""
	r = []
	for regexp in r_list:
		match = regexp.search(string)
		if match is not None:
			res_tuple = regexp, match
			r.append(res_tuple)
	if len(r) == 0:
		returnFalse
	else:
		return r

def process_info_dict(d):
	"""Given a dictionary describing the various prompts and strings a mud sends at login, convert all items that mbf is expecting to be regular expressions into compiled re objects.
	Args:
		d: the dictionary to process
	returns: The same dictionary with expected regexp objects updated in place to become so
	"""
	if type(d) != dict:
		raise TypeError("This function expects a dictionary", type(d))
	for k, v in d.iteritems():
		if k.endswith('_prompt') or k.endswith('_wrong') or k.endswith('_correct'):
			if type(v) == str:
				v = re.compile(v)
				d[k] = v
	return d