import requests
import os
import sys
import json
import argparse

from html.parser import HTMLParser

import pprint as pp
from html5print import HTMLBeautifier




with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "configs", "config.json")) as f:
	config = json.load(f)
	SESSION = config["SESSION"]


class GameParser(HTMLParser):
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
		

def get_game_info(url):
	cookies = {
		"session" : SESSION
	}

	r = requests.get(url, cookies=cookies)

	html = r.content
	html = HTMLBeautifier.beautify(html, 4)

	return html


def get_submitted_countries(server):
	GAME_URL = config[f"{server.upper()}_GAME_URL"]
	parser = GameParser()
	html = get_game_info(GAME_URL)

	parser.feed(html)

	return parser.players




def main():
	argparser = argparse.ArgumentParser(description='API for backstabbr')
	argparser.add_argument("server", help="name of server (atm: h or brown)")
	parserArgs = argparser.parse_args()
	pp.pprint(get_submitted_countries(parserArgs.server))




	

if __name__ == "__main__":
	main()