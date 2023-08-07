from __future__ import annotations
from typing import Optional
from discord import SlashOption
import nextcord
from nextcord.ext import commands, tasks
import dotenv
dotenv.load_dotenv("tokens.env")
import os
from Mongo import Mongo
from UserContact import UserContact
from Buttons import ConfirmDialogue
from CommonUtils import *
from UofT import UofT

# ------------ GLOBAL OBJECTS AND VARIABLES ------------
contact = UserContact()
database = Mongo(os.getenv('PYMONGO'), "TTBTrackr")
ttb = commands.Bot(command_prefix='ttb', intents=nextcord.Intents.all())
ttb.add_cog(UofT(ttb, database, contact))

# ------------ BOT EVENTS ------------
@ttb.event
async def on_ready():
    print(f'{ttb.user} has connected to Discord!')
    await ttb.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="UofT Courses"))

# ------------ PROFILE-RELATED COMMANDS ------------
@ttb.slash_command(name="profile", description="Setup or update your TTBTrackr profile")
async def setup_profile(interaction: nextcord.Interaction,
                        instagram_username: Optional[str] = SlashOption(
                            name="instagram_username", description="The Instagram profile you want the bot to alert you on when vacancies are found"),
                        cell_number: Optional[str] = SlashOption(name="cell_number", description="The cell-phone number you want the bot to text when vacancies are found")):
    user_id = interaction.user.id
    profile = {}
    if instagram_username:
        profile["instagram"] = instagram_username
    if cell_number:
        # validate the cell number
        if not validate_phone_number(cell_number):
            await interaction.response.send_message("Invalid phone number. Please try again. Note that this bot only supports Canadian phone numbers for SMS", ephemeral=True)
            return
        profile["phone"] = cell_number
        
    if not database.is_user_in_db(user_id):
        database.add_user(user_id, profile)
        await interaction.response.send_message("Successfully setup your profile! Make sure to follow [@ttbtrackr](https://www.instagram.com/ttbtrackr/) on Instagram to get notified when we DM!", ephemeral=True)
    else:
        # User does not have a profile, create a new one.
        database.update_user_profile(user_id, profile)
        await interaction.response.send_message("Your profile has been updated!", ephemeral=True)

@ttb.slash_command(name="viewprofile", description="View your TTBTrackr profile")
async def view_profile(interaction: nextcord.Interaction):
    user_id = interaction.user.id
    if not database.is_user_in_db(user_id):
        await interaction.response.send_message("You don't have a profile to view!", ephemeral=True)
        return
    profile = database.get_user_profile(user_id)
    embed = nextcord.Embed(title="Your TTBTrackr Profile", description="Here is your profile information", color=nextcord.Color.blue())
    
    text_mappings = {"instagram": "Instagram Username", "phone": "Phone Number"}
    
    # Add the user's discord profile picture
    embed.set_thumbnail(url=interaction.user.avatar.url)
    for key in profile:
        embed.add_field(name=text_mappings[key], value=profile[key], inline=False)
    embed.set_footer("To update your profile, use /profile")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@ttb.slash_command(name="deleteprofile", description="Delete all information about your profile from TTBTrackr")
async def delete_profile(interaction: nextcord.Interaction) -> None:
    # First, check if the user has a profile
    if not database.is_user_in_db(interaction.user.id):
        await interaction.response.send_message("You don't have a profile to delete!", ephemeral=True)
    
    # For obvious reasons, we need to ask the user if they're sure
    confirm = ConfirmDialogue()
    message = await interaction.response.send_message(embed=build_embed_from_json("Embeds/delete_profile_warning.json"), ephemeral=True, view=confirm)
    await confirm.wait()
    await message.delete()
    if confirm.value:
        database.remove_user(interaction.user.id)
        await interaction.followup.send("Your profile has been deleted. We're sad to see you go 😢", ephemeral=True)
    else:
        await interaction.followup.send("Canceled", ephemeral=True)
    
# ------------ HELP-RELATED COMMANDS ------------
@ttb.slash_command(name="help", description="Get help with TTBTrackr")
async def help(interaction: nextcord.Interaction, module: str = SlashOption(name="module", description="The module you want help with", required=True, choices=["UofT"])):
    embed = build_embed_from_json(f"Embeds/{module}_help.json")
    await interaction.response.send_message(embed=embed)


ttb.run(os.getenv('DEVTOKEN'))