from __future__ import annotations
import json
import re
from typing import Optional
from discord import SlashOption
import nextcord
from nextcord.ext import commands, tasks
import dotenv
import os
import phonenumbers
from TTBAPI import TTBAPI
from Mongo import Mongo
from UserContact import UserContact
from Buttons import ConfirmDialogue

dotenv.load_dotenv("tokens.env")

contact = UserContact()

database = Mongo(os.getenv('PYMONGO'), "TTBTrackr")

intents = nextcord.Intents.all()

ttbapi = TTBAPI()

ttb = commands.Bot(command_prefix='ttb', intents=intents)

@ttb.event
async def on_ready():
    print(f'{ttb.user} has connected to Discord!')
    await ttb.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="UofT Courses"))

def build_embed_from_json(json_path: str) -> nextcord.Embed:
    # Load the embed data from the JSON file
    with open(json_path, "r") as file:
        embed_data = json.load(file)

    # Create the embed using the loaded data
    embed = nextcord.Embed(
        title=embed_data["title"],
        description=embed_data["description"],
        color=embed_data["color"]
    )

    for field_data in embed_data["fields"]:
        embed.add_field(
            name=field_data["name"],
            value=field_data["value"],
            inline=field_data["inline"]
        )

    return embed

@tasks.loop(seconds=60)
async def scrape():
    """
    Method which actively checks the UofT API for changes in course status.
    """
    #  Step 1: Get a list of all users in the db
    await ttb.wait_until_ready()
    users = database.get_all_users()
    for user in users:
        # Step 2: Get the user's activities
        activities = database.get_user_activities(user)
        for activity in activities:
            # Step 3: Use the TTBAPI to check for changes in the course status
            try:
                if ttbapi.check_for_free_seats(activity["courseCode"], activity["Semester"], activity["Activity"]):
                    # Step 4: If there is a change, send a message to the user
                    discord_user = ttb.get_user(user)
                    await discord_user.send(f"Your course {activity['courseCode']} {activity['Activity']} has a spot open! Act fast!")
                    contact.contact_user(database.get_user_profile(user), f"Your course {activity['courseCode']} {activity['Activity']} has a spot open! Act fast!")
                    # Finally, remove the activity from the database
                    database.remove_user_activity(user, activity["courseCode"], activity["Semester"], activity["Activity"])
            except Exception as e:
                # Ping techmaster04 if there is an error
                # userID 516413751155621899
                user = ttb.get_user(516413751155621899)
                await user.send(f"""Something went wrong while scraping. Here is the relevant information:
                ```
                User ID: {user} ({ttb.get_user(user).name})
                Course code: {activity['courseCode']}
                Activity: {activity['Activity']}
                Semester: {activity['Semester']}
                Error: {e}
                ```""")

scrape.start()


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
    

@ttb.slash_command(name="help", description="Get help with TTBTrackr")
async def help(interaction: nextcord.Interaction):
    embed = build_embed_from_json("Embeds/help.json")
    await interaction.response.send_message(embed=embed)
    

@ttb.slash_command(name="viewtracked", description="View all the courses you're tracking")
async def view_tracked(interaction: nextcord.Interaction):
    if not database.is_user_in_db(interaction.user.id) or len(database.get_user_activities(interaction.user.id)) == 0:
        embed = build_embed_from_json("Embeds/no_tracked_courses.json")
        await interaction.response.send_message(embed=embed)
        return
    activities = database.get_user_activities(interaction.user.id)
    embed = nextcord.Embed(title="Tracked Courses",
                           description="Here are all the courses you're tracking", color=nextcord.Color.blue())
    for activity in activities:
        embed.add_field(name=f"{activity['courseCode']} {activity['Activity']} {activity['Semester']}",
                        value=ttbapi.get_name_from_code(activity['courseCode'], activity['Semester']), inline=False)
    await interaction.response.send_message(embed=embed)


@ttb.slash_command(name="untrack", description="Remove a course from being tracked")
async def untrack(interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to untrack. Example: CSC148H5"), activity: str = SlashOption(name="activity", description="The activity code which you want to untrack. Example: LEC0101"), session: str = SlashOption(
    name="semester",
    description="The semester in which the course is offered. Example: Fall",
    choices={"Fall": "F", "Winter": "S", "Full Year": "Y"},
),):
    if not database.is_user_in_db(interaction.user.id) or len(database.get_user_activities(interaction.user.id)) == 0:
        # If the user is not in the database or is not tracking any courses, send an error message
        embed = build_embed_from_json("Embeds/no_tracked_courses.json")
        await interaction.response.send_message(embed=embed)
        return
    course_code, activity = course_code.upper(), activity.upper()
    if not validate_course(course_code, activity, session):
        # If the course code or activity code is invalid, send an error message
        await interaction.response.send_message("Invalid course code or activity code. Please try again.", ephemeral=True)
        return
    # Step 1: Check if the user is already tracking the course
    if not database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
        await interaction.response.send_message("You aren't tracking this course!", ephemeral=True)
        return
    # Step 2: Remove the course from the database
    database.remove_user_activity(
        interaction.user.id, course_code, session, activity)
    await interaction.response.send_message("Successfully removed the course from being tracked!", ephemeral=True)


@ttb.slash_command(name="track", description="Add a course to be tracked by the bot")
async def track(interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to track. Example: CSC148H5"), activity: str = SlashOption(name="activity", description="The activity code which you want to track. Example: LEC0101"), session: str = SlashOption(
    name="semester",
    description="The semester in which the course is offered. Example: Fall",
    choices={"Fall": "F", "Winter": "S", "Full Year": "Y"},
),):
    footer = "If you have any questions, DM @ttbtrackr on Instagram or @techmaster04 on Discord"
    course_code, activity = course_code.upper(), activity.upper()
    # Step 1: Validate the course code and activity
    if not validate_course(course_code, activity, session) and not ttbapi.validate_course(course_code, activity, session):
        # Send an ephemeral message to the user saying the course code is invalid
        await interaction.response.send_message("Invalid course code or activity. Please try again", ephemeral=True)
        return
    # Step 2: Check if the course is already being tracked
    if database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
        # Send an ephemeral message to the user saying the course is already being tracked
        await interaction.response.send_message("You are already tracking this course-activity combo", ephemeral=True)
        return
    
    if not database.is_user_in_db(interaction.user.id):
        database.add_user(interaction.user.id, {})
        footer = "If you want to recieve notifications outside of Discord DMs, use /profile to setup your profile"
    # Step 3.2: Add the course to the database
    database.add_user_activity(
        interaction.user.id, course_code, session, activity)
    embed = nextcord.Embed(title="Course Added", description=f"Successfully added {course_code} {activity} to your tracked courses", color=nextcord.Color.blue())
    embed.set_footer(text=footer)
    # Finally, send a message congratulating the user on adding the course
    await interaction.response.send_message(embed=embed)

def validate_course(course_code: str, activity: str, semester: str) -> bool:
    """
    Method which uses a regex to determine whether an entered course code is the valid syntax for a UofT course code.
    This method is a precursor to checking on the server whether the course code is valid, and is used to reduce strain on the API.
    """
    # Define the regular expression pattern for a valid UofT course code with specific format
    pattern_code = r'^[A-Z]{3}\d{3}[HY][135]$'
    match_code = re.match(pattern_code, course_code)
    pattern_activity = r'\b(PRA|LEC|TUT)\d{4}\b'
    match_activity = re.match(pattern_activity, activity)
    # We also need to make sure semester is in [F, S, Y]
    return bool(match_code) and bool(match_activity) and semester in ['F', 'S', 'Y']

def validate_phone_number(phone_number: str) -> bool:
    """
    Method which validates a phone number using the phonenumbers library
    """
    number = phonenumbers.parse(phone_number, "CA")
    return phonenumbers.is_valid_number_for_region(number, "CA")

ttb.run(os.getenv('DEVTOKEN'))