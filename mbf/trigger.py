# Mbf - the mud bot framework
# trigger class
# Author: Blake Oliver <oliver22213@me.com>

import re


class Trigger(object):
	def __init__(self, trig, is_regexp=True, case_sensitive=True, name=None, enabled=True, stop_processing=False, sequence=100):
		"""This class represents a trigger and it's metadata;
			It does not store code, as it's intended that a function in mbf will "decorate" user functions with a trigger class,
		Arguments:
			trig: Either a regular expression (prefered) or a plain text string (which will be matched literally)
			is_regexp: A boolean that specifies if the trigger argument is a regular expression (and if it's a string it will be compiled), or just a plain text string (which will be left alone and matched literally)
			case_sensitive: A bool, true by default, that specifies if the trigger will match characters in exact case.
				When this is false, regular expressions have the 'IGNORECASE' mode set; for strings, the trig value is 'lower()'-ed on instantiation, the incoming line is 'lower()'-ed as well and then processed.
			name: A string (none by default) that is the human readable name for the trigger.
				The name is set by default by mbf's 'trigger' method which wrapps the trigger's code; unless set otherwise it will become the name of the trigger's function.
			enabled: A boolean that determines if this trigger will be considered when matching lines.
				Triggers can be disabled when created, and when required, enabled by other code when needed.
			stop_processing: A bool, false by default, that tells the parser to stop firing triggers after this one.
			sequence: An integer (100 by default) that is used to determine the order in which triggers will be fired.
				Triggers will be fired from lowest sequence to highest; if any trigger tells the parser to stop firing, no more triggers (no matter their sequence) will be fired afterwards.
		"""
		self.trig = trig
		self.is_regexp = is_regexp
		self.case_sensitive = case_sensitive
		self.name = name
		self.enabled = enabled
		self.sequence = sequence
		
		pass # for now
	
	def add_function(f):
		"""Add a function to an instance of this class; this function will be what gets run when this trigger matches"""
		self.fn = f
	
	# Comparison methods, so that sort() will properly sort on sequence

	__eq__ = lambda self, other: self.sequence == other.sequence
	__ne__ = lambda self, other: self.sequence != other.sequence
	__lt__ = lambda self, other: self.sequence < other.sequence
	__le__ = lambda self, other: self.sequence <= other.sequence
	__gt__ = lambda self, other: self.sequence > other.sequence
	__ge__ = lambda self, other: self.sequence >= other.sequence