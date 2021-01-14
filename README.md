# backstabbr_api
Web-scraper API and Discord Bot for the online diplomacy program Backstabbr


### API Params
session_token: the cookie holding the token from the Game Master's login. Obtained by going to the game page as the GM and opening the developer console (ctrl-shift-I or cmd-shift-I on Chrome), clicking under Application --> Storage --> Cookies --> The link right below cookies, then copying the Value next to "session".

base_url: the base url for the Backstabbr game the API will watch. Typically in the form [https://www.backstabbr.com/game/<game_name>/<game_id>](https://www.backstabbr.com/game/<game_name>/<game_id>).


### Configs Guide
In the backstabbr_bot/configs folder, in order to get the bot to run correctly, two JSONs need to be created:
1. config.json: of the form
 {
  "<server_name>" : {
   "GAME_URL" : "<base_url>",
   "SESSION_TOKEN" : "<session_token>",
   "DISCORD_TOKEN" : "<discord_token>",
   "DISCORD_GUILD" : "<discord_guild>"
  }
 }
where <base_url> and <session_token> take the forms explained above, <discord_token> is the token for the discord bot, and <discord_guild> is the name of the discord server.
