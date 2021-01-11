import requests
import os
from dotenv import load_dotenv

from html.parser import HTMLParser

import pprint as pp
from html5print import HTMLBeautifier


load_dotenv()
GAME_URL=os.getenv("GAME_URL")
SESSION=os.getenv("SESSION")



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
			self.currentCountry = data.strip("\r\n\n ")

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


def get_submitted_countries():
	parser = GameParser()
	html = get_game_info(GAME_URL)

	parser.feed(html)

	return parser.players




def main():
	pp.pprint(get_submitted_countries())




	

if __name__ == "__main__":
	main()