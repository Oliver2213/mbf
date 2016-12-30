# Mbf, the mud bot framework
# Author: Blake Oliver <oliver22213@me.com>

import re
import telnetlib
import sys

from trigger import Trigger


class Mbf(object):
	
	def __init__(self, hostname, info, port=23, username=None, password=None, manage_login=True, autoconnect=True, reconnect=True):
		"""Constructor for the main Mbf class
		Args:
			hostname: the hostname of your mud; this isn't optional for obvious reasons.
			info: info should be a dictionary with values specific to your mud. Acceptable keys are below:
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
			autologin: Automatically log in after connecting. Requires that username and password are set and that manage_login is True, will do nothing otherwise. Set this to false if you want to manually login by running login().
		"""
		self.hostname = hostname
		self.info = info
		self.port = port
		self.manage_login = manage_login
		self.autoconnect = autoconnect
		self.autologin = autologin
		self.reconnect = reconnect
		
		if username and password:
			self.credentials={} # Create a credentials dict so later these values can be used in login command strings
			self.credentials['username'] = username
			self.credentials['password'] = password
		else: # we don't know username or password
			if self.autologin:
				self.autologin = False # we can't manage logins
		
		# self.connected is a boolean that indicates whether this instance of mbf is currently connected to a mud.
		# At first, this is set to false, but connect() sets this to the telnet object's 'eof'
		self.connected = False
		if self.autoconnect:
			self.connect()
		self.tn = None
	
	def connect(self):
		"""Method to connect to the provided host using the provided port. Method is ran automatically at class instantiation if autoconnect is set to true; also handles auto logins if that option is enabled"""
		self.tn = telnetlib.Telnet(self.hostname, self.port)
		self.connected = self.tn.eof
		# some handy Telnet class local mappings (for easing client implementation and easier wrapping if necessary):
		self.read_until = self.tn.read_until
		self.read_very_eager = self.tn.read_very_eager
		self.expect = self.tn.expect
		if self.autologin:
			self.login() # Start our autologin sequence
	
	def disconnect(self):
		"""Close the telnet connection"""
		self.tn.close()
	
	def send(self, msg, prefix = "", suffix = '\n'):
		"""'write' to the telnet connection, with the provided prefix and suffix. The provided type can be either a string (in which case it will be sent directly), or a list of strings (which will be iterated over and sent, in the order which the items were added."""
		if type(msg) == str:
			self.tn.write(prefix+msg+suffix)
		elif type(msg) == list:
			for command in list:
				self.tn.write(prefix+command+suffix)
	
	
	def login(self):
		"""Manage logging into a mud"""
		if 'username_prompt' in self.info.itervalues() == False:
			self.exit("Auto login failed, no username prompt provided. Please add this to your info dictionary passed to the framework's constructor")
		# We should be connected
		if self.info['pre_username']: # if we have commands to send before sending username_command
			self.send(self.info['pre_username']) # send them
		# We use telnetlib's 'read_until' because we want the call to block, in case the mud is slow
		self.read_until(self.info['username_prompt'])
		if self.info['username_command']:
			# Send the username command, providing the credentials dict so the user has access to username and password values
			send(self.info['username_command'] %(self.credentials))
		else: # No specific command for the username
			# Just send the username on it's own
			self.send(self.credentials['username'])
		
		l = [self.info['username_wrong']] # List of regexps we think might match
		if self.info['password_prompt']:
			l.append(self.info['password_prompt']) # We have a password prompt regexp, so we add it to the expected list of regexps
		r = self.expect(l)
		if l[r[0]] != self.info['username_wrong']: # if the matching regexp is not password_wrong
			if self.info['post_username']:
				self.send(self.info['post_username'])
		else: # incorrect username
			self.exit("Incorrect username.")
		
		if self.info['password_prompt'] and self.info['password_command'] and l[r[0]] == self.info['password_prompt']: # if we have a password prompt and command and the password prompt regexp matched
			# First, run pre_password commands if any:
			if self.info['pre_password']:
				self.send(self.info['pre_password'])
			# The mud is requesting a password, because our password_prompt regexp matched
			self.send(self.info['password_command'] %(self.credentials)) # Send the password command
			l = [self.info['password_wrong']] # again, list of regexp(s) we expect to match
			if self.info['password_correct']:
				l.append(self.info['password_correct']) # add the correct password regexp to the expected list of matches
			r = self.expect(l)
			if self.info['password_correct'] and l[r[0]] == self.info['password_correct']: # the password_correct regexp exists and matches
				# Login successful
				# do successful things here
				self.logged_in = True
				return True # Our work is done
			elif l[r[0]] != self.info['password_wrong']: # the password is incorrect, and we don't know what a successful password attempt looks like, so let's assume things worked
				# login assumed
				# do successful things here
				return True
			elif l[r[0]] == self.info['password_wrong']: # incorrect password regexp matched
				self.exit("Incorrect password.")
	
	def exit(self, reason, code=1):
		"""Centralized exiting function"""
		print(reason)
		print("Exiting.")
		if self.connected:
			self.disconnect()
		sys.exit(code)