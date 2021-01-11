import urllib
import os
import pprint as pp

with urllib.request.urlopen("https://www.backstabbr.com/game/Brown-25/6218974247518208") as response:
	html = response.read()

print(html)