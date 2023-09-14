# TTBTracker
Discord Bot which scrapes information from the TTB UofT database and alerts to vacancies in courses. By utilizing the same requests which https://ttb.utoronto.ca/ sends out, this bot is able to track open spots in classes and DM individuals looking to enroll/swap positions in a course without losing their current spot

# How it works 

## Initial Discoveries 
The majority of the work for this Discord Bot is derrived from my old Discord Bot [tTimeTable](https://github.com/IbraTech04/tTimeTable-Uni-Edition). Feel free to check out the repo for more information on how I was able to scrape the UofT TimeTable builder. The basic gist of it was using DevTools to find the request which returns the course information, then reverse-engineering the request to find the parameters which are sent to the server.

## Original Features + New Features
Originally the bot was only designed to send you a direct message (DM) on Discord when a spot opened up in a course. However, I have since added more ways for the bot to contact you, notably Instagram support \(through (InstagrAPI)[https://github.com/adw0rd/instagrapi]\) and SMS/Phone call support \(through (Twilio)[https://www.twilio.com/]\). 

# How to host it yourself
## Requirements
- Python 3.9+ (I personally test this on 3.9.13)
- A Discord Bot Token (You can get one from the [Discord Developer Portal](https://discord.com/developers/applications))
- A Twilio Account (You can get one from [Twilio](https://www.twilio.com/))
- An Instagram Account (You can get one from [Instagram](https://www.instagram.com/))
- A MongoDB Database (You can get one from [MongoDB](https://www.mongodb.com/))

## The .env file
The .env file is where you will store all of your secret keys and tokens. It should be named `tokens.env` and in the same directory as the `bot.py` file. The .env file should look like this:
```
DISCORD=
PYMONGO=
INSTAUSER=
INSTAPASS=
TWILIOAUTH
TWILIOSID=
TWILIONUM=
```
These are the fields which the program accesses. 


## DISCLAIMER
The InstagrAPI API is an unofficial API created by third-party developers and is not endorsed or supported by Instagram. By using this API, you acknowledge that it is not an official Instagram service, and you do so at your own risk.

Please be aware that Instagram's terms of service prohibit the use of unauthorized third-party APIs, and your account may be subject to actions, including suspension or termination, if detected by Instagram.

While I have personally used this API for an extended period without encountering any issues, I cannot guarantee the same experience for every user. The risks associated with using unofficial APIs should be considered, and you should exercise caution and discretion when deciding to use this API. I personally use this on a burner account as to not jeapordize my main account, and I recommend you do the same.

I am not liable for any consequences that may arise from using the InstagrAPI API, including but not limited to account issues, data loss, or any other adverse effects. It is your responsibility to understand and comply with Instagram's terms of service and API usage policies.


Now with the legal stuff out of the way, let's get back to the fun stuff!

## Running the bot
The main entry-point for this bot is `bot.py`. This bot takes a decent amount of time to start up, so be patient :P. You'll know the bot is ready when it outputs `<bot_name> has connected to Discord!` to the console.
