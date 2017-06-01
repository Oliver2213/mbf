# Mbf - the mud bot framework
# trigger class
# Author: Blake Oliver <oliver22213@me.com>

import re


class Trigger(object):
	def __init__(self, trig, is_regexp=True, case_sensitive=True, multiline=False, name=None, group='all', enabled=True, stop_processing=False, sequence=100):
		"""This class represents a trigger and it's metadata;
			It does not store code, as it's intended that a function in mbf will "decorate" user functions with a trigger class,
		Arguments:
			trig: Either a regular expression (prefered) or a plain text string (which will be matched literally)
			is_regexp: A boolean that specifies if the trigger argument is a regular expression (and if it's a string it will be compiled), or just a plain text string (which will be left alone and matched literally)
			case_sensitive: A bool, true by default, that specifies if the trigger will match characters in exact case.
				When this is false, regular expressions have the 'IGNORECASE' mode set; for strings, the trig value is 'lower()'-ed on instantiation, the incoming line is 'lower()'-ed as well and then processed.
			multiline: If this trigger should match on multiple lines.
			name: A string (none by default) that is the human readable name for the trigger.
				The name is set by default by mbf's 'trigger' method which wrapps the trigger's code; unless set otherwise it will become the name of the trigger's function.
			enabled: A boolean that determines if this trigger will be considered when matching lines.
				Triggers can be disabled when created, and when required, enabled by other code when needed.
			stop_processing: A bool, false by default, that tells the parser to stop firing triggers after this one.
			sequence: An integer (100 by default) that is used to determine the order in which triggers will be fired.
				Triggers will be fired from lowest sequence to highest; if any trigger tells the parser to stop firing, no more triggers (no matter their sequence) will be fired afterwards for that specific buffer of data.
		"""
		self.trig = trig
		self.is_regexp = is_regexp
		self.case_sensitive = case_sensitive
		self.multiline = multiline
		self.name = name
		self.group = group
		self.enabled = enabled
		self.sequence = sequence
		self.stop_processing = stop_processing
		if self.is_regexp:
			self.mode = 0  #flags for the re
			if self.case_sensitive == False:
				mode += re.IGNORECASE
			if self.multiline:
				self.mode += re.MULTILINE|re.DOTALL
			# After setting modes, compile the re pattern object with them
			self.trig = re.compile(self.trig, flags=self.mode) # compile into a re pattern object
		else:
			if self.case_sensitive == False:
				self.trig = self.trig.lower()
	
	def add_function(self, f):
		"""Add a function to an instance of this class; this function will be what gets run when this trigger matches
		It's signature should be as follows:
			text - The text that this trigger found a match in.
				For multiline triggers, this is the entire block of text that was pulled from the socket and passed to fire.
				For single line triggers, whether regexp or plaintext, this will be the single line that it matched in.
				If your trigger is multiline, this may be a large chunk of text; triggers using regular expressions will have a much easier time of parsing their line(s) from this data.
			match - If the trigger uses a regular expression, this will be it's corresponding match object. If the trigger is a plaintext string, this will be none.
				With this you can extract named (and unnamed) variables, split the string, and use any normal 're' match object methods.
		"""
		self.fn = f
	
	def matches(self, string):
		"""Determine if this    trigger instance matches string; return true if so, false if otherwise.
		This is meant for quick evaluation of a trigger, without running findall on a potentially large block of text, extracting all of the (potentially many) re matches for regular expression triggers.
		Note that this doesn't return how many times the specific trigger matches against the given string; just that it *does* match at some point, at least once.
		This method also properly handles triggers that are regular expressions and ones that are plaintext
		Args:
			string - a string to look in to see if this trigger matches at least once
		"""
		if self.is_regexp:
			if self.trig.search(string):
				return True
			else: # No matches for this regexp trigger on given string
				return False
		elif self.is_regexp == False:
			if self.trig in string:
				return True
			else: # text trigger string not found in given data
				return False
	
	def fire(self, string):
		"""Fires this trigger by running the function associated with it.
		This properly handles regexp and plain-text triggers, (both single and multiline), calling the associated function for every match in string.
		It is assumed that 'matches' has been called and has returned true; otherwise running this is a waist
		Args:
			string - a string of text to look for matches in.
		"""
		if self.is_regexp:
			if self.multiline == False: # split string up into lines
				for l in string.splitlines(): # And feed them to finditer
					for m in self.trig.finditer(l):	
						self.fn(l, m) # call the trigger's function
			elif self.multiline: # multiline trig
				# We can feed each trigger the hole block
				for m in self.trig.finditer(string): # for every occurrence of this trigger in given block of text
					self.fn(string, m) # call the trigger's function
		elif self.is_regexp == False:
			# Ugh, plain-text triggers
			if self.case_sensitive == False:
				string = string.lower()
			if self.multiline:
				if self.trig  in string:
					return self.fn(string, None)
			else: # not multiline
				# split string by lines
				lines = string.splitlines()
				# line by line text matching iteration
				for l in lines:
					if self.trig in l:
						return self.fn(string, None) # call associated function and return it's value
	
	def enable(self):
		"""Enable this trigger"""
		self.enabled = True
	
	def disable(self):
		"""Disable this trigger"""
		self.enabled = False
	
	# Comparison methods, so that sort() will properly sort on sequence

	__eq__ = lambda self, other: self.sequence == other.sequence
	__ne__ = lambda self, other: self.sequence != other.sequence
	__lt__ = lambda self, other: self.sequence < other.sequence
	__le__ = lambda self, other: self.sequence <= other.sequence
	__gt__ = lambda self, other: self.sequence > other.sequence
	__ge__ = lambda self, other: self.sequence >= other.sequence

	def __repr__(self):
		return """<trigger {}>""".format(self.name)