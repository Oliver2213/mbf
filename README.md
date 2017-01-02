#MBF - The Mud Bot Framework

Mbf is a small library to allow for easily creating mud bots. While MUDing might not be as popular as it once was, it's still thriving today and so are those wonderfully automatic, carefully coded (or not!), helpful (or harmful!), pieces of code we call bots. From the simple 2 trigger one alias to the bewilderingly complex, bots have existed in some form or another as long as people have been lazy (since like, forever). Usually you have a client which lets you send commands to the mud by typing them and (optionally) lets you make aliases and triggers. My personal favorite is [MUSHclient](http://www.gammon.com.au/mushclient/mushclient.htm), which supports all the bells and whistles of alias and trigger creation, packaging sets of these (plus timers and variables) up into plugins for fellow botters to use.  
There's only one problem: while it comes with lua working out of the box, and does support more than a handful of languages, getting python up and working with mush using it as the default scripting engine was sadly beyond me and those I know.
This bugged me, as I really like python, and botting; and mbf was born.

## Differences between mbf and normal clients

As mentioned above, normal clients are interactive. While some clients might optionally support triggers, aliases, timers and the lot, their primary purpose is to be used by a person at the keyboard.

Mbf, however, doesn't actually support interactive use out of the box; you can certainly add it in your code that uses the framework, or file a pull request if you'd like to add it to the framework. This is because primarily mbf is for bots, not people. This design choice doesn't really mean much in how you code your triggers, aside from the fact that you can't really have things controlled locally (with aliases you type) unless you code the mechanisms for that yourself. The advantages of this are that you can run your bots on a linux server somewhere and control it through the mud or in any other way you can think of; no need to run a full-blown client when all you want is to be able to run a bot.

## Features

* Mbf is a tiney standalone library; you don't need anything other than python and it's standard library to run it. This will most likely change in the future, as I have plans to implement a transparrent proxy with twisted.
* Easily associate your functions with their triggers with a decorator; sane options are set by default.
* Supports single and multiline regular expressions and plain text trigger strings (though regular expressions are recommended).
* Supports trigger sequencing; triggers with lowest sequences run first, followed by ones with higher and higher sequences.
* Any trigger can stop execution of other triggers for one buffer of data. This means that a low sequence trigger that either returns false, or has it's stop_processing flag set in the trigger decorator can stop higher sequenced triggers from running, but only on that particular block of data received from the mud.
* Triggers can be enabled or disabled individually or (if you use the group keyword with the trigger decorator), in groups. 
* Supports managing logins automatically. Before instantiating an instance of the Mbf class, you create a mud_info dictionary with the keys 'pre_username', 'username_prompt', 'username_command', 'username_wrong', 'post_username', 'pre_password', 'password_prompt', 'password_command', 'password_correct', 'password_wrong', and 'post_password'.  
Not all of these need to be specified; mbf will, for example, assume that the login was successful even if 'password_correct' is not set, as long as the 'password_wrong' regular expression doesn't match. You can also leave out the pre_* and post_* values if you don't need them; they are for navigating login menus or doing any special work to actually enter the mud. Read Mbf's docstring for more info on what each of these does and which ones need to be regular expressions. If you don't need or want this functionality, just set manage_login to false when calling mbf.
* Provides a send function with optional prefixes and suffixes so users don't have to 'write' to the telnet connection directly; you can also pass this lists of strings and each one will be sent sequentially.

## Example

Here's an example of making a simple tell trigger. It connects to the mud [Alter Aeon](https://alteraeon.com) and (when someone sends it a tell), responds with a random response, and tells it's "master" what the person told it. It also uses the mudinfo module, which I intend to hold configurations for several popular muds in the future.

```
# Mbf Test Bot!

import random
import mbf
from mbf.mudinfo import alter_aeon

master = 'dernan'
responses = [
	"I'm just a bot, and not a very smart one yet...",
	"Beep boop.",
	"I'm mbf!"
]

m = mbf.Mbf("alteraeon.com", alter_aeon, port=3010, username="your_username", password="your_password", autoconnect=False, auto_login=False)

# Triggers

@m.trigger(r"""(?P<name>[a-zA-Z]+) tells you\, \'(?P<message>.+)\'""")
def tell_received(t, match):
	"""Trigger that fires when a tell is received"""
	# t is the line that this trigger matched on
	# match is it's regular expression match object
	m.send("tell {} Tell from {}: {}".format(master, match.group("name"), match.group("message")))
	m.send("tell {} {}".format(match.group("name"), random.choice(responses)))

@m.trigger(r"""Enter Selection \-\>\s*""")
def login_menu(t, match):
	"""Encountered the login menu; send 1 to enter the game"""
	m.send("1")

def run():
	"""Run the test bot"""
	print("Connecting...")
	m.connect()
	print("Logging in...")
	m.login()
	print("Logged in.")
	m.send("tell {} Mbf test online".format(master))
	m.process_triggers()

if __name__ == '__main__':
	run()
```