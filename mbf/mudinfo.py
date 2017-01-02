# Mbf, the mud bot framework - mud info dictionary file

# This file contains mud_info dictionaries for mud(s) that I use;
# Later I'll probably update it to have more, but for now
# It's convenient for testing

alter_aeon = {
	'pre_username' : None, # No commands to send before username
	'username_prompt' : r"""Would you like to create a new character\?\s*""",
	'username_wrong' : r"""No character by that name found\.\s*""",
	'username_command' : """%(username)s""", # this is the default already
	'post_username' : None,
	'pre_password' : None,
	'password_prompt' : r"""Password\:""",
	'password_wrong' : r"""Wrong password\.""",
	'password_command' : """%(password)s""",
	'post_password' : None,
	'password_correct' : None
}