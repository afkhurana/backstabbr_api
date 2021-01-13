import requests
import os
import sys
import json
import argparse
import asyncio
from copy import deepcopy

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

# models shell class
class Models:
	class Message:
		def __init__(self, author=None, date=None):
			self.author = author
			self.date = date
			self.body_fragments = [] # inherently temp; does not affect __eq__() or __hash__()
			self.body = ""

		def __eq__(self, other):
			if isinstance(other, Models.Message):
				return (self.author == other.author and self.date == other.date and self.body == other.body)
			return False

		def __hash__(self):
			return hash(tuple([self.author, self.date, self.body]))

		def __str__(self):
			try:
				return f"{self.author.upper()}, {self.date.upper()}:\n{self.body}"
			except AttributeError as e:
				return f"{self.author}, {self.date}:\n{self.body}"				

		def create_body(self):
			self.body = "\n".join(self.body_fragments)
	
	class Thread:
		def __init__(self, thread_id, recipients=[], messages=[]): # messages is array of Message
			self.thread_id = thread_id
			self.recipients = recipients
			self.messages = messages

		def __eq__(self, other):
			if isinstance(other, Models.Thread):
				return (self.thread_id == other.thread_id and self.recipients == other.recipients and self.messages == other.messages)
			return False

		def __hash__(self):
			return hash(tuple(self.thread_id, self.recipients, self.messages))

		def __str__(self):
			str_messages = '\n'.join([str(message) for message in self.messages])
			return f"{self.thread_id},\n{self.recipients},\n{str_messages}"

		def add_recipient(self, country):
			self.recipients.append(country)

		def add_message(self, message):
			self.messages.append(message)



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
	def __init__(self, thread_id):
		HTMLParser.__init__(self)
		self.thread = Models.Thread(thread_id)
		
		self._inTags = []

		self._pcount = 0
		self._divcount = 0

		# self._buffer = 1


	def handle_starttag(self, tag, attrs):
		if tag == "p" and "message_body" in self._inTags:
			self._pcount += 1
			# print(f"\t(increment pcount to {self._pcount})")

		elif tag == "div" and "press-thread-body" in self._inTags:
			self._divcount += 1

		# flags
		if tag == "p" and ("class", "from") in attrs:
			self._inTags.append("from")

		elif tag == "div" and ("id", "press-thread-body") in attrs:
			self._inTags.append("press-thread-body")

		elif tag == "div" and ("class", "message") in attrs:
			self._inTags.append("message")
			# we are starting a new message so we can reset tempMessage
			self.thread.add_message(Models.Message())

		elif tag == "p" and ("class", "byline") in attrs:
			self._inTags.append("byline")

		elif tag == "em" and "byline" in self._inTags:
			# we are in an em inside a byline
			self._inTags.append("em")

		elif tag == "em" and "from" in self._inTags:
			# we are in a from line
			self._inTags.append("em")

		elif tag == "p" and ("class", "body") in attrs:
			assert ( self._pcount == 0 )
			self._inTags.append("message_body")


	def handle_data(self, data):
		data = data.strip("\r\n\n ")
		if data == "":
			return

		if "from" in self._inTags:
			if "em" in self._inTags:
				self.thread.add_recipient(data)

		elif "message" in self._inTags:
			if "message_body" in self._inTags:
				self.thread.messages[-1].body_fragments.append(data)

			elif "em" in self._inTags:
				self.thread.messages[-1].author = data

			# should only run if we are in a byline but not an em
			elif "byline" in self._inTags:
				assert ( data.startswith("in ") )
				self.thread.messages[-1].date = data[3:]

			# should only run if outside byline and message_body
			elif "message" in self._inTags:
				pass

			elif "press-thread-body" in self._inTags: 
				pass


	def handle_endtag(self, tag):
		if tag == "p" and self._pcount > 0:
			# runs if inside body
			self._pcount -= 1
			# print(f"\t(decriment pcount to {self._pcount})")

		elif tag == "p" and "message_body" in self._inTags:
			self._inTags.pop()

		elif tag == "em" and "em" in self._inTags:
			self._inTags.pop()

		elif tag == "p" and "byline" in self._inTags:
			self._inTags.pop()

		elif tag == "p" and "from" in self._inTags:
			self._inTags.pop()

		elif tag == "div" and self._divcount > 1:
			# runs if inside message
			self._divcount -= 1

		elif tag == "div" and self._divcount == 1:
			# runs if closing message

			assert (self._inTags == ["press-thread-body", "message"])
			self.thread.messages[-1].create_body()
			self._inTags.pop()
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

		html = r.text
		# html = HTMLBeautifier.beautify(html, 4)

		return html

	def get_submitted_countries(self):
		parser = _SubmittedParser()
		html = self.__get_html(self.base_url)
		parser.feed(html)

		return parser.players

	async def wait_for_submitted_update(self):
		original_players = self.get_submitted_countries()
		new_players = deepcopy(original_players)

		while new_players == original_players:
			new_players = self.get_submitted_countries()
			await asyncio.sleep(self.refresh_time)
		return new_players

	def get_press_threads(self):
		parser = _PressListParser()
		html = self.__get_html(self.base_url + "/pressthread")
		parser.feed(html)

		return parser.thread_ids

	def get_press_thread(self, thread_id):
		parser = _PressThreadParser(thread_id)
		html = self.__get_html(self.base_url + "/pressthread/" + thread_id)

		try:
			parser.feed(html)
		# debugging. generates html file and prints pos if assertionerror
		except AssertionError as e:
			print(parser.getpos())
			print(parser.thread)
			with open("foo_assertionerror.html", "w") as f:
				f.write(html)
			raise e

		return parser.thread

	async def wait_for_thread_updates(self):
		original_thread_ids = self.get_press_threads()
		new_thread_ids = deepcopy(original_thread_ids)

		original_top_thread = self.get_press_thread(original_thread_ids[0])
		new_top_thread = deepcopy(original_top_thread)

		while (original_thread_ids == new_thread_ids) and (original_top_thread == new_top_thread):
			new_thread_ids = self.get_press_threads()
			new_top_thread = self.get_press_thread(new_thread_ids[0])
			await asyncio.sleep(self.refresh_time)

		return new_top_thread