from __future__ import annotations
from discord import SlashOption
import nextcord
from nextcord.ext import commands
import dotenv
dotenv.load_dotenv("tokens.env")
import os
from Mongo import Mongo
from UserContact import UserContact
from CommonUtils import *
from UofT import UofT
from Profiles import ProfilesCog

# ------------ GLOBAL OBJECTS AND VARIABLES ------------
contact = UserContact()
if os.getenv("COMPUTERNAME").upper() == "IBRAPC":
    database = Mongo(os.getenv('PYMONGO'), "TTBTrackrDev")
else:
    database = Mongo(os.getenv('PYMONGO'), "TTBTrackr")
ttb = commands.Bot(command_prefix='ttb', intents=nextcord.Intents.all())
ttb.add_cog(UofT(ttb, database, contact))
ttb.add_cog(ProfilesCog(ttb, database))

# ------------ BOT EVENTS ------------
@ttb.event
async def on_ready():
    print(f'{ttb.user} has connected to Discord!')
    await ttb.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="UofT Courses"))
    
# ------------ HELP-RELATED COMMANDS ------------
@ttb.slash_command(name="help", description="Get help with TTBTrackr")
async def help(interaction: nextcord.Interaction, module: str = SlashOption(name="module", description="The module you want help with", required=True, choices=["UofT"])):
    embed = build_embed_from_json(f"Embeds/{module}_help.json")
    await interaction.response.send_message(embed=embed)

computer_name = os.getenv('COMPUTERNAME')
if computer_name.upper() == "IBRAPC":
    ttb.run(os.getenv('DEVTOKEN'))
else:
    ttb.run(os.getenv('DISCORD'))