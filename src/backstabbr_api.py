import requests
import os
import sys
import json
import argparse
import asyncio

from html.parser import HTMLParser

import pprint as pp
from html5print import HTMLBeautifier



class _SubmittedParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.inTags = []
		self.currentCountry = None
		self.submitted = False
		self.players = {}

	def handle_starttag(self, tag, attrs):
		# flag/reinitialize if notable, return if not
		if tag == "tr":
			if attrs == [("class", "playerlist")]:
				self.inTags.append("class playerlist")
				self.currentCountry = None
				self.submitted = False
			return
		if "class playerlist" not in self.inTags:
			return

		# at this point, we are inside a playerlist

		# flag to ID country
		if tag == "div":
			if attrs == [("class", "country")]:
				self.inTags.append("class country")

		# check for clock
		elif tag == "i":
			if attrs == [("class", "fas fa-clock text-info")]:
				self.submitted = True

		return


	def handle_data(self, data):
		# we only need this to run if we're checking for country name
		if "class country" in self.inTags:
			data = data.strip("\r\n\n ")
			if data == "":
				return
			self.currentCountry = data

		return


	def handle_endtag(self, tag):
		# we don't need to parse if we're not in a playerlist
		if "class playerlist" not in self.inTags:
			return

		# handle end of playerlist
		if tag == "tr":
			assert ( self.inTags == ["class playerlist"] )
			self.inTags.pop()
			self.players[self.currentCountry] = self.submitted

		# remove class country flag
		elif tag == "div":
			if self.inTags[-1] == "class country":
				self.inTags.pop()

		return

# parser that takes in a http://base.url/pressthread and grabs all thread_ids
class _PressListParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.thread_ids = [] # strings

	def handle_starttag(self, tag, attrs):
		if tag == "a":
			for name, value in attrs:
				if name == "id":
					assert ( value.startswith("thread_") )
					self.thread_ids.append(value[7:])


class _PressThreadParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.thread_ids = []

	def handle_starttag(self, tag, attrs):
		pass

	def handle_data(self, data):
		pass

	def handle_endtag(self, tag):
		pass

		
class BackstabbrAPI:
	def __init__(self, session_token, base_url):
		self.session_token = session_token
		self.base_url = base_url

	def __get_game_info(self, url):
		cookies = {
			"session" : self.session_token
		}

		r = requests.get(url, cookies=cookies)

		html = r.content
		html = HTMLBeautifier.beautify(html, 4)

		return html

	def get_submitted_countries(self):
		parser = _SubmittedParser()
		html = self.__get_game_info(self.base_url)
		parser.feed(html)

		return parser.players

	async def wait_for_submitted_update(self):
		original_players = self.get_submitted_countries()
		new_players = original_players
		while new_players == original_players:
			new_players = self.get_submitted_countries()
			await asyncio.sleep(30)
		return new_players

	def get_press(self):
		parser = _PressListParser()
		html = self.__get_game_info(self.base_url + "/pressthread")
		parser.feed(html)

		return parser.thread_ids
