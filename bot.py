from __future__ import annotations
import nextcord
from nextcord.ext import commands, tasks
import dotenv
dotenv.load_dotenv("tokens.env")
import os
from Mongo import Mongo
from UserContact import UserContact
from CommonUtils import *
from UofT import UofT
from Profiles import ProfilesCog
import random
from AdminCommands import AdminCommands
from CommonUtils import get_most_recent_file_modified_time
ttb = commands.Bot(command_prefix='ttb', intents=nextcord.Intents.all(), owner_id=516413751155621899)


# ------------ GLOBAL OBJECTS AND VARIABLES ------------
contact = UserContact()
if os.getenv("COMPUTERNAME"):
    database = Mongo(os.getenv('PYMONGO'), "TTBTrackrDev")
else:
    database = Mongo(os.getenv('PYMONGO'), "TTBTrackr")
ttb.add_cog(UofT(ttb, database, contact))
ttb.add_cog(ProfilesCog(ttb, database, contact))
# ttb.add_cog(AdminCommands(ttb, database))

VERSION = "TTBTrackr v2023.9.1PRERELEASE_BETA\n"

# ------------ BOT EVENTS ------------
@ttb.event
async def on_ready():
    print(f'{ttb.user} has connected to Discord!')
    await update_status()

    
# ------------ HELP-RELATED COMMANDS ------------
@ttb.slash_command(name="help", description="Get help with TTBTrackr")
async def help(interaction: nextcord.Interaction):
    """
    The main header command for help
    This command should not be invoked since it's a header
    """
    pass

@help.subcommand(name="profile", description="Get help with profiles")
async def help_profile(interaction: nextcord.Interaction):
    """
    Help with profiles
    """
    await interaction.response.send_message(embed=build_embed_from_json("Embeds/profile_help.json"))

@help.subcommand(name="uoft", description="Get help with the UofT Module")
async def help_uoft(interaction: nextcord.Interaction):
    await interaction.response.send_message(embed=build_embed_from_json("Embeds/UofT_help.json"))

@help.subcommand(name="about", description="Get information about TTBTrackr")
async def about(interaction: nextcord.Interaction):
    # Load the embed data from the JSON file
    with open("Embeds/about.json", "r", encoding="utf-8") as file:
        embed_data = json.load(file)
    embed_data['fields'][0]['value'] = VERSION + f"Last patched <t:{int(get_most_recent_file_modified_time())}:R>"
    for _, cog in ttb.cogs.items():
        embed_data['fields'][1]['value'] += cog.version + "\n"
    await interaction.response.send_message(embed=build_embed_from_json(embed_data))

@help.subcommand(name="contact", description="Get information about TTBTrackr's Contact Methods")
async def contact(interaction: nextcord.Interaction):
    vcard_file = nextcord.File("ttbtrackr.vcf")
    await interaction.response.send_message("Tip: Add TTBTrackr to your contacts by downloading this VCard file!", embed=build_embed_from_json("Embeds/contact_info.json"), file=vcard_file)

@tasks.loop(minutes=30)
async def update_status():
    await ttb.wait_until_ready()
    type_mapping = {"watching": nextcord.ActivityType.watching, "playing": nextcord.ActivityType.playing, "listening": nextcord.ActivityType.listening, "competing": nextcord.ActivityType.competing}
    statusses = json.load(open("common_strings.json", "r"))["presence"]
    rand_status = random.choice(statusses)
    text = rand_status['text']
    type = rand_status['type']
    await ttb.change_presence(activity=nextcord.Activity(type=type_mapping[type], name=text))
update_status.start()
    
computer_name = os.getenv('COMPUTERNAME')
if computer_name:
    ttb.run(os.getenv('DEVTOKEN'))
else:
    ttb.run(os.getenv('DISCORD'))