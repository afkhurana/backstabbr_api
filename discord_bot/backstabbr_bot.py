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

from src.backstabbr_api import BackstabbrAPI


# parse sys.argv
argparser = argparse.ArgumentParser()
argparser.add_argument("server", help="name of server to watch (must match config.json)")
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
backstabbr_api = BackstabbrAPI(SESSION_TOKEN, GAME_URL)




@bot.event
async def on_ready():
	for guild in bot.guilds:
		if guild.name == DISCORD_GUILD:
			print(f'{bot.user} is listening to guild {guild.name}')
			break





@bot.command(name="bot", ignore_extra=True)
async def backstabbr(ctx, *args):
	if len(args) < 2:
		return

	if args[0] == "remind" and args[1] == "orders":
		# load countries
		with open(os.path.join("configs", "backstabbr_countries.json")) as f:
			backstabbr_countries = json.load(f)[sysargs.server]

		# retrieve list from api
		sent_orders = backstabbr_api.get_submitted_countries()
		ids_to_send = [user_id for country, user_id in backstabbr_countries.items() if sent_orders[country] == False]

		# message users
		message = "The following countries still need to send orders:\n"
		for user_id in ids_to_send:
			message += f"{get(ctx.guild.members, id=int(user_id)).mention}\n"
		await ctx.send(message)





bot.run(DISCORD_TOKEN)
