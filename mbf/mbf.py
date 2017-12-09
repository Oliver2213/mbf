# Mbf, the mud bot framework
# Author: Blake Oliver <oliver22213@me.com>

import re
import telnetlib
import select
import sys
import threading
import time
import logging


from apscheduler.schedulers.background import BackgroundScheduler

from trigger import Trigger
from timer import Timer
from utils import match_regexp_list, process_info_dict


class Mbf(object):
	
	def __init__(self, hostname, mud_info, port=23, username=None, password=None, auto_login=True, manage_login=True, autoconnect=True, reconnect=True, timeout=3, trigger_delay=0.1):
		"""Constructor for the main Mbf class
		Args:
			hostname: the hostname of your mud; this isn't optional for obvious reasons.
			mud_info: a dictionary with values specific to your mud. Items that end in '_prompt', '_wrong', and '_correct' must be regular expressions; if you provide strings they will be automatically compiled into regular expression objects.
			Acceptable keys are below:
				pre_username: Any commands mbf should send to your mud before it can send a username. This can be either none, a string, or a list (in the last case, the commands will be executed sequentially in the order they were added to the list).
				username_prompt: The string your mud sends when it's asking for your account's username. This should be a regular expression, either a compiled object or a string.
				username_wrong: If your mud sends a string informing you that you entered an incorrect username, set that as this item's value so mbf can exit. This should be a regular expression, either a compiled object or a string.
				username_command: The string to send your username to the mud. This isn't limited to just the username; If your mud requires you to connect like: connect username password, then a matching value for this item would be: "connect %(username)s %(password)s". If this is left out or is set to none, the username on it's own will be sent.
				post_username: Any commands that should be sent to your mud after sennding the username. Either a string, or a list of strings is acceptable; strings in a list will be sent in the order in which they were added to the list. This can safely be left out of your info dict if you don't need it, or set to none. If 'username_command' sends your password as well (and therefore 'password_command' and 'password_prompt' are not set or are none), you should use this item to navigate any menus or screens your mud presents before actually logging you in. These commands will not be sent if the username is incorrect.
				pre_password: If you need to send any commands before entering a password, they will go here. This item can be either a string or a list. If a list, strings in the list will be sent sequentially in the order that they were added to the list. This item can safely be left out of your info dict if you don't need it, or set to none. If 'password_command' and 'password_prompt' are not set or are none, these commands will not be sent.
				password_prompt: A string that your mud sends to prompt you for your password. In some cases, it might just be "password:", and on some muds that require you to connect with "connect user password", this can be safely left out or set to none. This should be a regular expression, either a compiled object or a string. If this and 'password_command' are set to none or are left out, the framework will not send any password, assuming that the password was sent by the username command.
				password_wrong: If your mud sends a string to let you know your password is incorrect (which it almost certainly does), set this here so that the framework can exit. This should be a regular expression, either a compiled object or a string.
				password_command: If your mud requires a command other than the password itself, set that here. For example, on a mud that requires you to send the word password before your password, you would set this to: "password %(password)s". If this and 'password_prompt' are set to none or are left out, the framework will not send any password, assuming that the password was sent by the username command. Unlike username_command, mbf will *not* automatically send the password on it's own. If you need to send the password on it's own, you must explicitly set this to "%(password)s". Lets say password some more: password password password this better not be your password.
				post_password: If your mud has any kind of menu system or you just want to run a command after sending your password, you can use this item to specify command(s) you want the framework to send. This can either be a string, a list, or none / left out. If a list is provided, items will be sent sequentially as they were added to the list. If 'password_command' and 'password_prompt' are not set or are none, these commands will not be sent. Also, if the password_wrong regexp is matched, these commands will not be sent.
				password_correct: If your mud sends any kind of welcome string when you correctly enter your password (which it probably does), set this item. This needs to be a regular expression, and this message should be sent *only* if the login is successful. If this is left out or is set to none, (and 'password_wrong' is provided), then after sending 'password_command' if 'password_wrong' isn't received the login is assumed to be successful and trigger processing begins. If this is set, post_password commands get sent after receiving this.

			port: port for your mud, defaults to 23 for what I hope are also obvious reasons.
			Username: The username of your mud. You don't *have* to provide this here, but it will let mbf reconnect. If you for some reason don't want to provide this here, you can always use write() to send it manually yourself.
			Password: your mud account's password. As with username, you don't have to specify it here, but it helps if you want mbf to reconnect you and manage your logins.
			manage_login: Should the framework worry about managing the login sequence? If set to true, the framework will use the values in the info dictionary to handle logging into the mud. Values like 'prompt_username', 'username_command', 'prompt_password', and 'password_command' are some of the values that the framework will use to correctly log in. If this is set to false, the user will need to make their own triggers for dealing with this. This is set to true by default.
			autoconnect: automatically connect to the mud using hostname and port upon instance instantiation. This *does not* automatically log you in. Set this to false if you want to connect manually by calling connect().
			auto_login: Automatically log in after connecting. Requires that username and password are set, that appropriate values are set in the info dict, and that manage_login is True, will do nothing otherwise. Set this to false if you want to manually login by running login() after running connect(). Note that login() has the same requirements, minus, of course, that this boolean be set to True.
			timeout: The default timeout when expecting regular expressions from the mud. This is set to 3 seconds by default; if your network or that of the mud is slow you can increase this and mbf will wait longer when expecting.
			trigger_delay: The amount of time for the trigger processor thread to sleep in between reading chunks of data from the socket. This is usually something you won't need to mess with; it's just here so that the CPU doesn't spike needlessly.
		"""
		self.log = logging.getLogger("mbf")
		self.log.addHandler(logging.NullHandler())
		self.log.info("Initializing")
		self.hostname = hostname
		self.mud_info = process_info_dict(mud_info)
		self.port = port
		self.manage_login = manage_login
		self.autoconnect = autoconnect
		self.auto_login = auto_login
		self.reconnect = reconnect
		self.timeout = timeout
		self.trigger_delay = trigger_delay
		self.triggers = []
		self.timers = []
		self.stopped = threading.Event() # the event that when set will stop trigger processing
		self.scheduler = BackgroundScheduler()
		self.g = {} # global dictionary for client code to store things in
		
		if username and password:
			self.log.debug("A username and password were both provided")
			self.credentials={} # Create a credentials dict so later these values can be used in login command strings
			self.credentials['username'] = username
			self.credentials['password'] = password
		else: # we don't know username or password
			if self.auto_login:
				self.log.warn("Mbf was told to manage logins, but was not provided a username and password; disabling automatic login management")
				self.auto_login = False # we can't manage logins
		
		# self.connected is a boolean that indicates whether this instance of mbf is currently connected to a mud.
		# At first, this is set to false, but connect() sets this to the telnet object's 'eof'
		self.connected = False
		if self.autoconnect:
			self.log.debug("Autoconnecting")
			self.connect()
		self.log.info("Initialized")

	def connect(self):
		"""Method to connect to the provided host using the provided port. Method is ran automatically at class instantiation if autoconnect is set to true; also handles auto logins if that option is enabled"""
		self.log.info("""Connecting to host {}, port {}""".format(self.hostname, self.port))
		self.tn = telnetlib.Telnet(self.hostname, self.port)
		self.log.debug("Connection established")
		self.connected = self.tn.eof
		self.log.debug("Running on_connect callback")
		self.on_connect()
		# some handy Telnet class local mappings (for easing client implementation and easier wrapping if necessary):
		self.read_until = self.tn.read_until
		self.read_very_eager = self.tn.read_very_eager
		self.expect = self.tn.expect
		if self.auto_login and self.manage_login:
			self.log.info("Automatically logging in after connecting")
			self.login() # Start our autologin sequence
	
	def disconnect(self):
		"""Close the telnet connection"""
		self.log.info("Disconnected")
		self.tn.close()
		self.stop_processing()
		self.log.debug("Calling on_disconnected callback")
		self.on_disconnect(self, True) # a deliberate disconnect

	def send(self, msg, prefix = "", suffix = '\n'):
		"""'write' to the telnet connection, with the provided prefix and suffix. The provided type can be either a string (in which case it will be sent directly), or a list of strings (which will be iterated over and sent, in the order which the items were added)."""
		self.log.debug("""Sending to the mud: {}""".format(prefix+msg+suffix))
		try:
			if type(msg) == str:
				self.tn.write(prefix+msg+suffix)
			elif type(msg) == list:
				for command in list:
					self.tn.write(prefix+command+suffix)
		except EOFError as e:
			self.log.error("""Could not send "{}"; connection broken""".format(prefix+msg+suffix))
			# the connection is broken
			self.stop_processing()
			self.log.debug("Calling on_disconnect callback")
			self.on_disconnect(False)
			return False
	
	
	def login(self):
		"""Manage logging into a mud"""
		self.log.info("Logging in")
		if 'username_prompt' in self.mud_info.keys() == False or self.mud_info['username_prompt'] == None:
			self.exit("Auto login failed, no username prompt provided. Please add this to your info dictionary passed to the framework's constructor")
		# We should be connected
		if self.mud_info['pre_username']: # if we have commands to send before sending username_command
			self.log.debug("Commands need to be sent before sending the username")
			self.send(self.mud_info['pre_username']) # send them
			self.log.debug("Done sending pre-username commands")
		# We use telnetlib's expect method because it waits until it matches a list of regexps
		self.log.debug("Expecting the username prompt")
		r = self.expect([self.mud_info['username_prompt']], self.timeout)
		self.log.debug("""Expect returned {}""".format(r))
		if r[0] == -1 and r[1] == None: # expect timed out because username_prompt didn't match or didn't arrive within timeout
			self.exit("Timeout while waiting for username prompt! \nThis could mean your username_prompt regular expression is incorrect or your network connection or that of the mud is too slow for the set timeout. \nMake sure your login_prompt regular expression is matching on your mud's login string, check your network connection, and try increasing the timeout value.")
		else:
			# we know it matched because if r[0] was anything other than -1, expect() didn't time out, and returned an index insead;
			# the username prompt is the only item in the list
			self.log.debug("Matched username prompt")
		if self.mud_info['username_command']:
			# Send the username command, providing the credentials dict so the user has access to username and password values
			self.log.debug("Sending username command")
			self.send(self.mud_info['username_command'] %(self.credentials))
		else: # No specific command for the username
			# Just send the username on it's own
			self.log.debug("No specific username command was provided; just sending the username on it's own")
			self.send(self.credentials['username'])
		
		l = [self.mud_info['username_wrong']] # List of regexps we think might match
		self.log.debug("Added the wrong_username regexp to the list of regular expressions we're looking to match")
		if self.mud_info['password_prompt']:
			l.append(self.mud_info['password_prompt']) # We have a password prompt regexp, so we add it to the expected list of regexps
			self.log.debug("Added the password_prompt regexp to the list of regular expressions we're looking to match")
		self.log.debug("Expecting a regular expression")
		# we're expecting either the username_wrong regexp, or the password_prompt one as well, if it's given
		r = self.expect(l, self.timeout)
		if r[0] == -1 and r[1] == None:
			# No regular expression matched
			if self.mud_info['password_prompt']: # a password prompt was given, but it did not match; exit
				self.exit("Timeout while waiting for either the incorrect username or password prompt regular expressions to match! \nThis could mean your wrong_username or password_prompt regular expressions are not matching or your network connection or that of the mud is too slow for the set timeout. \nMake sure your wrong_username and password_prompt regular expressions are matching on your mud's strings, check your network connection, and try increasing the timeout value.")
		elif l[r[0]] != self.mud_info['username_wrong']: # if the matching regexp is not username_wrong
			self.log.debug("The regular expression matched was not the one for an incorrect username")
			if self.mud_info['post_username']:
				self.log.debug("Sending post-username commands")
				self.send(self.mud_info['post_username'])
		else: # incorrect username
			self.exit("Incorrect username.")
		
		if self.mud_info['password_prompt'] and self.mud_info['password_command'] and l[r[0]] == self.mud_info['password_prompt'] and self.mud_info['password_prompt'] != None: # if we have a password prompt and command (and the prompt is not none) and the password prompt regexp matched
			self.log.debug("Password prompt and command were given, and the matching regular expression is password_correct")
			# First, run pre_password commands if any:
			if self.mud_info['pre_password']:
				self.log.debug("Running pre-password commands")
				self.send(self.mud_info['pre_password'])
			# The mud is requesting a password, because our password_prompt regexp matched
			self.log.debug("Sending password command")
			self.send(self.mud_info['password_command'] %(self.credentials)) # Send the password command
			l = [self.mud_info['password_wrong']] # again, list of regexp(s) we expect to match
			self.log.debug("Added the password_wrong regular expression to the list of expected matches")
			if self.mud_info['password_correct']:
				l.append(self.mud_info['password_correct']) # add the correct password regexp to the expected list of matches
				self.log.debug("Added the password_correct regular expression to the list of expected matches")
			self.log.debug("Expecting a password-related regular expression to match")
			r = self.expect(l, self.timeout)
			if r[0] == -1 and r[1] == None:
				self.exit("Timeout while waiting for either the password_correct or password_wrong regular expressions to match.\rThis usually means one of them is written incorrectly. Check them, as well as the strings your mud sends, or try increasing the timeout value.")
			elif l[r[0]] == self.mud_info['password_correct']: # the password_correct regexp matches
				# Login successful
				self.log.info("Successfully logged in")
				# do successful things here
				self.logged_in = True
				return True # Our work is done
			elif r[0] == -1 and r[1] == None: # the password isn't incorrect, the expect timed out and we don't know what a successful password attempt looks like, so let's assume things worked
				# login assumed
				self.log.info("Assumed successful login ")
				# do successful things here
				self.logged_in = True
				return True
			elif l[r[0]] == self.mud_info['password_wrong']: # incorrect password regexp matched
				self.exit("Incorrect password.")
	
	def exit(self, reason="", code=0):
		"""Centralized exiting function"""
		if reason is not "":
			if code==0:
				self.log.info("Exiting - "+reason)
			else:
				self.log.critical("Exiting - "+reason)
		else:
			if code == 0:
				self.log.info("Exiting")
			else:
				self.log.critical("Exiting")
		self.stop_processing()
		if self.connected:
			self.disconnect()
		sys.exit(code)
	
	def start_processing(self, print_output=False):
		"""Begin trigger processing and start the scheduler
		args:
			print_output: Send what the mud sends to stdin before executing triggers.
		"""
		self.log.debug("Starting processing")
		self.print_output = print_output
		self.log.debug("Sorting triggers")
		self.triggers.sort() # put the trigger list in order of sequence
		self.log.debug("Triggers sorted")
		self.log.debug("Starting background scheduler")
		self.scheduler.start()
		self.log.debug("Background scheduler started")
		if self.stopped.is_set():
			self.log.debug("Stop was set; cleared")
			self.stopped.clear()
		self.log.debug("Starting trigger processor thread")
		t = threading.Thread(name="trigger_processor", target=process_triggers, args=(self,))
		t.start()
		self.log.debug("Trigger processor started")
		self.log.info("Processing started")	

	def stop_processing(self):
		"""Stop the scheduler and the trigger processing thread."""
		self.log.debug("Stopping processing")
		if self.scheduler.running:
			self.log.debug("Background scheduler is running; shutting down")
			self.scheduler.shutdown()
			self.log.debug("Background scheduler shut down")
		if not self.stopped.is_set():
			self.stopped.set()
			self.log.debug("Stop flag for trigger processor set; that thread should end soon")
	
	def on_connect(self):
		"""Callback that subclasses can override to do something when the connection is established to the mud."""
		pass
	
	def on_disconnect(self, deliberate=False):
		"""Callback that subclasses can override to do something when the connection to the mud gets broken.
Args:
	deliberate: True if the connection was deliberately broken by the framework (e.g. disconnect() was called), false if otherwise.
		"""
		pass
	
	def trigger(self, *t_args, **t_kwargs):
		"""Method that returns a decorator to automatically set up a trigger and associate it with a function to run when the trigger is matched
		Code in this function gets executed immediately, not when the associated function runs.
		It dynamically accepts arguments and passes them off to a 'Trigger' class instance
		"""
		# This would be the logical place to create the trigger object
		# but we can't because the next function is the one that accepts the trigger function as it's argument
		# And we need to be able to tell the trigger object what it's associated function is
		def decorator(trigger_function):
			"""This takes the trigger's associated function as the only argument
			It defines the decorator and wrapper, as well as setting up the 'Trigger' object and associating it with the decorated function.
			"""
			if 'name' not in t_kwargs: # No name for this trigger was provided; use trigger's function name
				t_kwargs['name'] = trigger_function.__name__
			# Create an instance of the 'Trigger' class
			new_trigger = Trigger(*t_args, **t_kwargs)  # provide all wrapper arguments to this 'trigger' instance
			def wrapper(*args, **kwargs):
				"""This function is what will be called in place of the decorated function;
				It takes the arguments given to it and passes them on.
				It needs to run said function and return what it does or (if it doesn't return anything), return the value of the stop_processing flag in the trigger class
				"""
				r = trigger_function(*args, **kwargs) # call the original trigger function
				return r or new_trigger.stop_processing
			new_trigger.add_function(wrapper) # Associate the wrapper with the trigger object
			# add the trigger to an internal list
			self.triggers.append(new_trigger)
			return wrapper
		return decorator
	
	def enable_trigger(self, name):
		"""Enable the trigger with given name"""
		self.log.debug("Enable trigger {}".format(name))
		[t.enable() for t in self.triggers if t.name == name]
	
	def disable_trigger(self, name):
		"""Disable the trigger with given name"""
		self.log.debug("Disable trigger {}".format(name))
		[t.disable() for t in self.triggers if t.name == name]
	
	def enable_trigger_group(self, group):
		"""Enable all triggers in the given group"""
		self.log.debug("Enable trigger group {}".format(group))
		[t.enable() for t in self.triggers if t.group == group]
	
	def disable_trigger_group(self, group):
		"""Disable all triggers in the given group"""
		self.log.debug("Disable trigger group {}".format(group))
		[t.disable() for t in self.triggers if t.group == group]
	
	def enable_timer(self, name):
		"""Enable the timer with given name"""
		self.log.debug("Enable timer {}".format(name))
		[t.enable() for t in self.timers if t.name == name]
	
	def disable_timer(self, name):
		"""Disable the timer with given name"""
		self.log.debug("Disable timer {}".format(name))
		[t.disable() for t in self.timers if t.name == name]
	
	def enable_timer_group(self, group):
		"""Enable all timers in the given group"""
		self.log.debug("Enable timer group {}".format(group))
		[t.enable() for t in self.timers if t.group == group]
	
	def disable_timer_group(self, group):
		"""Disable all timers in the given group"""
		self.log.debug("Disable timer group {}".format(group))
		[t.disable() for t in self.timers if t.group == group]
	
	def timer(self, *t_args, **t_kwargs):
		"""Method that returns a decorator to automatically set up a timer and associate it with a function to run at the specified time
		Code in this function gets executed immediately, not when the associated function runs.
		It dynamically accepts arguments and passes them off to a 'Timer' class instance
		"""
		def decorator(timer_function):
			"""This takes the timer's associated function as the only argument
			It defines the decorator and wrapper, as well as setting up the 'Timer' object and associating it with the decorated function.
			"""
			if 'name' not in t_kwargs: # No name for this timer was provided; use function name
				t_kwargs['name'] = timer_function.__name__
			# Create an instance of the 'Timer' class
			new_timer = Timer(self.scheduler, *t_args, **t_kwargs)  # provide a reffrence to the scheduler and all wrapper arguments to this instance
			def wrapper(*args, **kwargs):
				"""This function is what will be called in place of the decorated function;
				It takes the arguments given to it and passes them on to the provided function.
				"""
				r = timer_function(*args, **kwargs) # call the original trigger function
				return r
			new_timer.add_function(wrapper) # Associate the wrapper with the timer object
			# add the timer to an internal list
			self.timers.append(new_timer)
			return wrapper
		return decorator


def process_triggers(m):
	"""Function that handles trigger processing in the background."""
	log = logging.getLogger("mbf.trigger_processor")
	while not m.stopped.is_set():
		try:
			r, w, e = select.select([m.tn.sock], [], [])
			if r:
				buff = m.read_very_eager()
				log.debug("""Got buffer of data: {}""".format(buff))
				if m.print_output:
					for line in buff.strip().splitlines():
						if line != '':
							print(line)
				for t in m.triggers :
					if t.enabled and t.matches(buff):
						log.debug("""{} matches on something in the current buffer""".format(t))
						# Find all matches of this trigger in the buffer and call the associated function for each one
						# Basically, "fire" this trigger
						stp = t.fire(buff) # stop trigger processing if this returns true
						if stp: # if the trigger function returned true or the trigger has stop_processing set
							log.debug("""{} stopped processing for the current buffer""".format(t))
							break # Don't do any more trigger processing for this buffer of data
			time.sleep(m.trigger_delay)
		except EOFError as e: # connection is closed
			log.debug("EOF error when reading a buffer for trigger processing")
			m.stop_processing()
			m.on_disconnect(deliberate=False)
