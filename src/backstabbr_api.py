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
		self._inTags = []
		self.currentCountry = None
		self.submitted = False
		self.players = {}

	def handle_starttag(self, tag, attrs):
		# flag/reinitialize if notable, return if not
		if tag == "tr":
			if attrs == [("class", "playerlist")]:
				self._inTags.append("class playerlist")
				self.currentCountry = None
				self.submitted = False
			return
		if "class playerlist" not in self._inTags:
			return

		# at this point, we are inside a playerlist

		# flag to ID country
		if tag == "div":
			if attrs == [("class", "country")]:
				self._inTags.append("class country")

		# check for clock
		elif tag == "i":
			if attrs == [("class", "fas fa-clock text-info")]:
				self.submitted = True

		return


	def handle_data(self, data):
		# we only need this to run if we're checking for country name
		if "class country" in self._inTags:
			data = data.strip("\r\n\n ")
			if data == "":
				return
			self.currentCountry = data

		return


	def handle_endtag(self, tag):
		# we don't need to parse if we're not in a playerlist
		if "class playerlist" not in self._inTags:
			return

		# handle end of playerlist
		if tag == "tr":
			assert ( self._inTags == ["class playerlist"] )
			self._inTags.pop()
			self.players[self.currentCountry] = self.submitted

		# remove class country flag
		elif tag == "div":
			if self._inTags[-1] == "class country":
				self._inTags.pop()

		return

# private message model
class _Message():
	def __init__(self, author=None, date=None):
		self.author = author
		self.date = date
		self.body_fragments = []

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
		self.thread = {} # { (<author>, <date>) : <message_body>, (<author>, <date>) : <message_body>, .... }
		
		self._inTags = []

		self._tempMessage = _Message()
		self._pcount = 0
		self._divcount = 0

		self._buffer = 1


	def handle_starttag(self, tag, attrs):
		# print("-STARTTAG", tag, attrs)
		# increment counts
		if tag == "p" and "message_body" in self._inTags:
			self._pcount += 1
			# print(f"\tincrement _pcount to {self._pcount}")

		elif tag == "div" and "press-thread-body" in self._inTags:
			self._divcount += 1

		# flags
		if tag == "div" and ("id", "press-thread-body") in attrs:
			self._inTags.append("press-thread-body")
			# we are starting a new message so we can reset tempMessage
			self._tempMessage = _Message()

		elif tag == "div" and ("class", "message") in attrs:
			self._inTags.append("message")
			# print(f"\t(inTags: {self._inTags})")
			# print(f"\t(self._divcount: {self._divcount})")

		elif tag == "p" and ("class", "byline") in attrs:
			# print("byline")
			self._inTags.append("byline")
			self._buffer = 1
			# print("SET BUFFER TO 1")

		elif tag == "em" and "byline" in self._inTags:
			# we are in an em inside a byline
			self._inTags.append("em")

		elif tag == "p" and ("class", "body") in attrs:
			self._inTags.append("message_body")
			self._buffer += 1
			# print(f"(ENCOUNTERED MESSAGE_BODY. increment _buffer to {self._buffer})")


	def handle_data(self, data):
		data = data.strip("\r\n\n ")
		if data == "":
			return
		if "message" not in self._inTags:
			return
		# print("\n")
		# print(f"Data: {data}")
		# print(self._inTags)

		if "message_body" in self._inTags:
			# print("body data")
			self._tempMessage.body_fragments.append(data)

		elif "em" in self._inTags:
			self._tempMessage.author = data

		# should only run if we are in a byline but not an em
		elif "byline" in self._inTags:
			assert ( data.startswith("in ") )
			self._tempMessage.date = data[3:]

		# should only run if outside byline and message_body
		elif "message" in self._inTags:
			pass

		elif "press-thread-body" in self._inTags: 
			pass


	def handle_endtag(self, tag):
		# print("-ENDTAG", tag)

		if tag == "p" and self._pcount > 0:
			# runs if inside body
			self._pcount -= 1
			# print(f"\t(decriment _pcount to {self._pcount})")

		elif tag == "p" and "message_body" in self._inTags:
			if self._buffer:
				self._buffer -= 1
				# print("\nused body buffer")
				return
			# print("end message_body\n")
			self._inTags.pop()

		elif tag == "em" and "em" in self._inTags:
			self._inTags.pop()

		elif tag == "p" and "byline" in self._inTags:
			if self._buffer:
				self._buffer -= 1
				return
			self._inTags.pop()

		elif tag == "div" and self._divcount > 1:
			# runs if inside message
			self._divcount -= 1
			# print(f"\t(decriment _divcount to {self._divcount})")

		elif tag == "div" and self._divcount == 1:
			# runs if closing message
			# print(self._inTags)
			# print("CLOSING MESSAGE")
			# print("")
			# okay i'm gonna be honest, i don't know why _pcount isn't working or how to do this better
			# what i do know, is there are no divs inside message_body
			# so this is my fix
			if self._inTags == ["press-thread-body", "message", "message_body"] and self._pcount == 0 and self._buffer == 0:
				self._inTags = ["press-thread-body", "message"]

			assert (self._inTags == ["press-thread-body", "message"])
			self._inTags.pop()
			message = self._tempMessage
			# print(message.author, message.date, message.body_fragments)
			self.thread[(message.author, message.date)] = "\n".join(message.body_fragments)
			self._divcount -= 1


		elif tag == "div" and "press-thread-body" in self._inTags:
			self._inTags.pop()
			assert ( len(self._inTags) == 0 )

		
class BackstabbrAPI:
	def __init__(self, session_token, base_url, refresh_time=30):
		self.session_token = session_token
		self.base_url = base_url
		self.refresh_time = refresh_time

	def __get_html(self, url):
		cookies = {
			"session" : self.session_token
		}

		r = requests.get(url, cookies=cookies)

		html = r.content
		html = HTMLBeautifier.beautify(html, 4)

		return html

	def get_submitted_countries(self):
		parser = _SubmittedParser()
		html = self.__get_html(self.base_url)
		parser.feed(html)

		return parser.players

	async def wait_for_submitted_update(self):
		original_players = self.get_submitted_countries()
		new_players = original_players.copy()

		while new_players == original_players:
			new_players = self.get_submitted_countries()
			await asyncio.sleep(self.refresh_time)
		return new_players

	def get_press_threads(self):
		parser = _PressListParser()
		html = self.__get_html(self.base_url + "/pressthread")
		parser.feed(html)

		return parser.thread_ids

	def get_press_thread_content(self, thread_id):
		parser = _PressThreadParser()
		html = self.__get_html(self.base_url + "/pressthread/" + thread_id)

		try:
			parser.feed(html)
		# debugging. generates html file and prints pos if assertionerror
		except AssertionError as e:
			print(parser.getpos())
			pp.pprint(parser.thread)
			with open("foo_assertionerror.html", "w") as f:
				f.write(html)
			raise e

		return parser.thread

	async def wait_for_thread_updates(self):
		original_thread_ids = self.get_press_threads()
		new_thread_ids = original_thread_ids.copy()

		original_top_thread_content = self.get_press_thread_content(original_thread_ids[0])
		new_top_thread_content = original_top_thread_content.copy()

		while (original_thread_ids == new_thread_ids) and (original_top_thread_content == new_top_thread_content):
			new_thread_ids = self.get_press_threads()
			new_top_thread_content = self.get_press_thread_content(new_thread_ids[0])
			await asyncio.sleep(self.refresh_time)

		return new_top_thread_content