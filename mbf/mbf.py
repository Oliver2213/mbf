# Mbf, the mud bot framework
# Author: Blake Oliver <oliver22213@me.com>

import re
import telnetlib


class Mbf(object):
	
	def __init__(self, hostname, info, port=23, username=None, password=None, manage_login=True, autoconnect=True, reconnect=True):
		"""Constructor for the main Mbf class
		Args:
			hostname: the hostname of your mud; this isn't optional for obvious reasons.
			info: info should be a dictionary with values specific to your mud. Acceptable keys are below:
				pre_username: Any commands mbf should send to your mud before it can send a username. This can be either none, a string, or a list (in the last case, the commands will be executed sequentially in the order they were added to the list).
				username_prompt: The string your mud sends when it's asking for your account's username. This should not be a regular expression.
				username_wrong: If your mud sends a string informing you that you entered an incorrect username, set that as this item's value so mbf can exit.
				username_command: The string to send your username to the mud. This isn't limited to just the username; If your mud requires you to connect like: connect username password, then a matching value for this item would be: "connect %(username)s %(password)s". If this is left out or is set to none, the username on it's own will be sent.
				post_username: Any commands that should be sent to your mud after sennding the username. This can safely be left out of your info dict if you don't need it, or set to none.
				pre_password: If you need to send any commands before entering a password, they will go here. This item can be either a string or a list. If a list, strings in the list will be sent sequentially in the order that they were added to the list. This item can safely be left out of your info dict if you don't need it, or set to none.
				password_prompt: A string that your mud sends to prompt you for your password. In some cases, it might just be "password:", and on some muds that require you to connect with "connect user password", this can be safely left out or set to none. This should not be a regular expression. If this and 'password_command' are set to none or are left out, the framework will not send any password, assuming that the password was sent by the username command.
				password_wrong: If your mud sends a string to let you know your password is incorrect (which it almost certainly does), set this here so that the framework can exit.
				password_command: If your mud requires a command other than the password itself, set that here. For example, on a mud that requires you to send the word password before your password, you would set this to: "password %(password)s". If this and 'password_prompt' are set to none or are left out, the framework will not send any password, assuming that the password was sent by the username command. Lets say password some more: password password password this better not be your password.
				post_password: If your mud has any kind of menu system or you just want to run a command after sending your password, you can use this item to specify command(s) you want the framework to send. This can either be a string, a list, or none / left out. If a list is provided, items will be sent sequentially as they were added to the list.

			port: port for your mud, defaults to 23 for what I hope are also obvious reasons.
			Username: The username of your mud. You don't *have* to provide this here, but it will let mbf reconnect. If you for some reason don't want to provide this here, you can always use write() to send it manually yourself.
			Password: your mud account's password. As with username, you don't have to specify it here, but it helps if you want mbf to reconnect you and manage your logins.
			manage_login: Should the framework worry about managing the login sequence? If set to true, the framework will use the values in the info dictionary to handle logging into the mud. Values like 'prompt_username', 'username_command', 'prompt_password', and 'password_command' are some of the values that the framework will use to correctly log in. If this is set to false, the user will need to make their own triggers for dealing with this. This is set to true by default.
			autoconnect: automatically connect to the mud using hostname and port upon instance instantiation. This *does not* automatically log you in. Set this to false if you want to connect manually by calling connect().
			autologin: Automatically log in after connecting. Requires that username and password are set and that manage_login is True, will do nothing otherwise. Set this to false if you want to manually login by running login().
		"""
		self.hostname = hostname
		self.info = info
		self.credentials={}
		self.credentials['username'] = username
		self.credentials['password'] = password
		self.port = port
		self.manage_login = manage_login
		self.autoconnect = autoconnect
		self.autologin = autologin
		self.reconnect = reconnect
		
		# self.connected is a boolean that indicates whether this instance of mbf is currently connected to a mud.
		At first, this is set to false, but connect() sets this to the telnet object's 'eof'
		self.connected = False
		if self.autoconnect:
			self.connect()

	def connect(self):
		"""Method to connect to the provided host using the provided port. Method is ran automatically at class instantiation if autoconnect is set to true"""
		self.tn = telnetlib.Telnet(self.hostname, self.port)
		self.connected = self.tn.eof
	
	def disconnect(self):
		"""Close the telnet connection"""
		self.tn.close()
	
	def send(self, msg, prefix = "", suffix = '\n'):
		"""'write' to the telnet connection, with the provided prefix and suffix"""
		self.tn.write(suffix+msg+prefix)
	