from __future__ import annotations
import re
from typing import Optional
from discord import SlashOption
import nextcord
from nextcord.ext import commands, tasks
import dotenv
import os
from TTBAPI import TTBAPI
from Mongo import Mongo
from instagrapi import Client
import twilio.rest

account_sid = 'AC2b1a7015a561484c6b94c1550f79c011'
auth_token = os.getenv("TWILIOAUTH")
twilio_client = twilio.rest.Client(account_sid, auth_token)

database = Mongo(os.getenv('PYMONGO'), "TTBTrackr")

dotenv.load_dotenv("tokens.env")
intents = nextcord.Intents.all()

ttbapi = TTBAPI()

ttb = commands.Bot(command_prefix='ttb', intents=intents)

insta_client = Client()
insta_client.login(os.getenv("INSTAUSER"), os.getenv("INSTAPASS"))


@ttb.event
async def on_ready():
    print(f'{ttb.user} has connected to Discord!')
    await ttb.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="UofT Courses"))


def contact_user_instagram(username: str, message: str):
    """
    Method which uses the InstagrAPI to send a message to a user's Instagram account.
    """
    send_to = insta_client.user_id_from_username(username=username)
    insta_client.direct_send(text=message, user_ids=[send_to])


def contact_user_sms(phone_number: str, message: str):
    """
    Sends an SMS message to a user's phone number.
    """
    message = twilio_client.messages.create(
        from_='+18506600835',
        body=message,
        to=str(phone_number)
    )

# Dict to make it easier to call the contact methods
contact_methods = {"instagram": contact_user_instagram,
                   "phone": contact_user_sms}


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
            if ttbapi.check_for_free_seats(activity["courseCode"], activity["Semester"], activity["Activity"]):
                # Step 4: If there is a change, send a message to the user
                discord_user = ttb.get_user(user)
                await discord_user.send(f"Your course {activity['courseCode']} {activity['Activity']} has a spot open! Act fast!")

                user_profile = database.get_user_profile(user)
                for method in user_profile:
                    contact_methods[method](
                        user_profile[method], f"Your course {activity['courseCode']} {activity['Activity']} has a spot open! Act fast!")

                # Finally, remove the activity from the database
                database.remove_user_activity(
                    user, activity["courseCode"], activity["Semester"], activity["Activity"])

scrape.start()


@ttb.slash_command(name="profile", description="Setup or update your profile for the bot")
async def setup_profile(interaction: nextcord.Interaction,
                        instagram_username: Optional[str] = SlashOption(
                            name="instagram_username", description="The Instagram profile you want the bot to alert you on when vacancies are found"),
                        cell_number: Optional[int] = SlashOption(name="cell_number", description="The cell-phone number you want the bot to text when vacancies are found")):
    user_id = interaction.user.id

    if database.is_user_in_db(user_id):
        # User already has a profile, allow updating the existing profile.
        await update_profile(interaction, user_id, instagram_username, cell_number)
    else:
        # User does not have a profile, create a new one.
        await create_profile(interaction, user_id, instagram_username, cell_number)


async def create_profile(interaction: nextcord.Interaction, user_id: int, instagram_username: Optional[str], cell_number: Optional[int]):
    profile = {}
    if instagram_username:
        profile["instagram"] = instagram_username
    if cell_number:
        profile["phone"] = cell_number

    database.add_user(user_id, profile)
    await interaction.response.send_message("Successfully setup your profile! Make sure to follow @ttbtrackr on Instagram to get notified when we DM!", ephemeral=True)


async def update_profile(interaction: nextcord.Interaction, user_id: int, instagram_username: Optional[str], cell_number: Optional[int]):
    profile_updates = {}
    if instagram_username:
        profile_updates["instagram"] = instagram_username
    if cell_number:
        profile_updates["phone"] = cell_number

    database.update_user_profile(user_id, profile_updates)
    await interaction.response.send_message("Your profile has been updated!", ephemeral=True)


@ttb.slash_command(name="help", description="Get help on how to use the bot")
async def help(interaction: nextcord.Interaction):
    embed = nextcord.Embed(
        title="TTBTrackr Help", description="A bot which tracks UofT courses for you and notifies you when a spot opens up", color=nextcord.Color.blue())
    embed.add_field(name="Setup", value="To setup or update your profile, use /profile. This command is required to be run before adding courses to be tracked. TTBTrackr contacts you over Discord DMs by default, however can also be configured to send you a text message or Instagram DM. While not required, they are reccomended. If you don't feel comfortable, no worries! TTBTrackr can run perfectly fine without them!", inline=False)
    embed.add_field(name="Adding Courses", value="To add a course to be tracked, use /track. You will need to provide the course code (With H/Y and campus codes), semester, and activity code you want to track. For example, if you want to track CSC148H5 LEC0101 in the Fall, you would use /track CSC148H5 LEC0101 F. You can find the course code and activity code on the UofT timetable website. The semester is either F, S, or Y for Fall, Winter, or Full Year respectively.", inline=False)
    embed.add_field(name="Removing Courses", value="To remove a course from being tracked, use /untrack. You will need to provide the course code (With H/Y and campus codes), semester, and activity code you want to remove. For example, if you want to remove CSC148H5 LEC0101 in the Fall, you would use /untrack CSC148H5 LEC0101 F. You can view all the courses you're tracking by using /viewtracked", inline=False)
    embed.add_field(name="Viewing tracked courses",
                    value="To view all the courses you're tracking, use /viewtracked. This will send you a list of all the courses you're tracking", inline=False)
    await interaction.response.send_message(embed=embed)


@ttb.slash_command(name="viewtracked", description="View all the courses you're tracking")
async def view_tracked(interaction: nextcord.Interaction):
    if not database.is_user_in_db(interaction.user.id):
        await interaction.response.send_message("You need to setup your profile before tracking courses. Use /profile to begin", ephemeral=True)
        return
    activities = database.get_user_activities(interaction.user.id)
    embed = nextcord.Embed(title="Tracked Courses",
                           description="Here are all the courses you're tracking", color=nextcord.Color.blue())

    if len(activities) == 0:
        embed.add_field(name="No Courses Tracked",
                        value="You're not tracking any courses! Use /track to begin tracking courses", inline=False)
        await interaction.response.send_message(embed=embed)
        return

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
    if not database.is_user_in_db(interaction.user.id):
        await interaction.response.send_message("You need to setup your profile before tracking courses. Use /profile to begin", ephemeral=True)
        return
    course_code, activity = course_code.upper(), activity.upper()
    if not validate_course(course_code, activity, session):
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
async def add(interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to track. Example: CSC148H5"), activity: str = SlashOption(name="activity", description="The activity code which you want to track. Example: LEC0101"), session: str = SlashOption(
    name="semester",
    description="The semester in which the course is offered. Example: Fall",
    choices={"Fall": "F", "Winter": "S", "Full Year": "Y"},
),):

    if not database.is_user_in_db(interaction.user.id):
        await interaction.response.send_message("You need to setup your profile before tracking courses. Use /profile to begin", ephemeral=True)
        return
    course_code, activity = course_code.upper(), activity.upper()
    # Step 1: Validate the course code and activity
    if not validate_course(course_code, activity, session):
        # Send an ephemeral message to the user saying the course code is invalid
        await interaction.response.send_message("Invalid course code or activity. Please try again", ephemeral=True)
        return
    # Step 2: Check if the course is already being tracked
    if database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
        # Send an ephemeral message to the user saying the course is already being tracked
        await interaction.response.send_message("You are already tracking this course-activity combo", ephemeral=True)
        return

    # Step 3: Add the course to the database
    # Step 3.1: Check if the user is in the database. If not, add them
    if not database.is_user_in_db(interaction.user.id):
        database.add_user(interaction.user.id)

    # Step 3.2: Add the course to the database
    database.add_user_activity(
        interaction.user.id, course_code, session, activity)
    # Finally, send a message congratulating the user on adding the course
    await interaction.response.send_message(f"Successfully added {course_code} {activity} to your tracked courses", ephemeral=True)


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


ttb.run(os.getenv('DISCORD'))
