import sys
sys.path.append("..")

import os
import discord
from discord.ext import commands, tasks
from discord.utils import get
import re
import json
import datetime
import pprint as pp
import asyncio
import argparse

from backstabbr_api import BackstabbrAPI, Models


# parse sys.argv
argparser = argparse.ArgumentParser()
argparser.add_argument("server", help="name of server to watch (must match config.json)")
argparser.add_argument("--refresh", help="refresh time for watch/loops", default='30')
argparser.add_argument('--test', action="store_true")
sysargs = argparser.parse_args()


# load configs
with open(os.path.join("configs", "config.json")) as f:
	config = json.load(f)[sysargs.server]
	DISCORD_TOKEN = config["DISCORD_TOKEN"]
	DISCORD_GUILD = config["DISCORD_GUILD"]
	GAME_URL = config["GAME_URL"]
	SESSION_TOKEN = config["SESSION_TOKEN"]


# initialize client
intents = discord.Intents()
intents = intents.all()
bot = commands.Bot(command_prefix="backstabbr!", intents=intents)



# initialize API
backstabbr_api = BackstabbrAPI(SESSION_TOKEN, GAME_URL, refresh_time=int(sysargs.refresh))




class Util:
	def __init__(self, *args, **kwargs):
		self.args = args
		self.kwargs = kwargs

	def load_countries():
		global backstabbr_countries
		with open(os.path.join("configs", "backstabbr_countries.json")) as f:
			backstabbr_countries = json.load(f)[sysargs.server]
		return backstabbr_countries

	def get_submitted_ids():
		sent_orders = backstabbr_api.get_submitted_countries()
		ids_to_send = []
		for country, user_id in backstabbr_countries.items():
			if country == "You":
				continue
			if not sent_orders[country]:
				ids_to_send.append(user_id)
		return ids_to_send


# load configs
backstabbr_countries = Util.load_countries()




@bot.event
async def on_ready():
	for guild in bot.guilds:
		if guild.name == DISCORD_GUILD:
			print(f'{bot.user} is listening to guild {guild.name}')
			break


@bot.event
async def on_command_error(ctx, error):
	# suppress check traceback
	if isinstance(error, commands.errors.CheckFailure):
		return

def server_correct():
	async def predicate(ctx):	
		return ctx.guild.name == DISCORD_GUILD
	return commands.check(predicate)


@bot.command(name="remind", ignore_extra=True)
@server_correct()
async def remind(ctx, *args):	
	if args == []:
		ctx.send("What am I reminding?")
		return

	# reload countries
	Util.load_countries()

	if args[0] == "orders":
		# retrieve list from api
		ids_to_send = Util.get_submitted_ids()

		# message users
		message = "The following countries still need to send orders:\n"
		for user_id in ids_to_send:
			message += f"{get(ctx.guild.members, id=int(user_id)).mention}\n"
		await ctx.send(message)


class Press(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.on_press_change.start()

	def cog_unload(self):
		self.on_press_change.cancel()

	@tasks.loop()
	@server_correct()
	async def on_press_change(self):
		new_thread = await backstabbr_api.wait_for_thread_updates() # Models.Thread
		if sysargs.test:
			print("Received message")

		Util.load_countries()

		for recipient in new_thread.recipients:
			if sysargs.test:
				print("Recipient")
			# do not notify if user wrote most recent message
			if recipient == new_thread.messages[-1].author:
				continue
			user = self.bot.get_user(backstabbr_countries[recipient])
			dm_channel = await user.create_dm()

			message = ("You received a press message. View it on backstabbr:\n"
						f"{GAME_URL}")
			await dm_channel.send(message)




bot.add_cog(Press(bot))
bot.run(DISCORD_TOKEN)
