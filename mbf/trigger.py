# Mbf - the mud bot framework
# trigger class
# Author: Blake Oliver <oliver22213@me.com>

import re


class Trigger(object):
	def __init__(name, regexp, enabled=True, multiline=False, 