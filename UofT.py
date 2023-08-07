"""
UofT-related timetable tracking functions 
This file contains all the classes required to track courses at UofT
This file was created in an attempt to modularize each university, to make it easier to 
add more universities in the future
"""
import re
import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import commands, tasks
from TTBAPI import TTBAPI, CourseNotFoundException, InvalidActivityException
from Mongo import Mongo
from Buttons import ConfirmDialogue
from CommonUtils import *
from UserContact import UserContact

class UofT(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Mongo, contact: UserContact) -> None:
        self.bot = bot
        self.ttbapi = TTBAPI()
        self.utils = UofTUtils()
        self.database = database
        self.contact = contact
        self.refresh.start()

    @tasks.loop(seconds=45)
    async def refresh(self) -> None:
        """
        Method which actively checks the UofT API for changes in course status.
        And notifies users when their desired course is availible
        """
        await self.bot.wait_until_ready()
        #  Step 1: Get a list of all users in the db
        users = self.database.get_all_users()
        for user in users:
            # Step 2: Get the user's activities
            activities = self.database.get_user_activities(user)
            for activity in activities:
                # Step 3: Use the TTBAPI to check for changes in the course status
                try:
                    if self.ttbapi.check_for_free_seats(activity["courseCode"], activity["Semester"], activity["Activity"]):
                        # Step 4: If there is a change, send a message to the user
                        discord_user = self.bot.get_user(user)
                        await discord_user.send(f"Your course {activity['courseCode']} {activity['Activity']} has a spot open! Act fast!")
                        self.contact.contact_user(self.database.get_user_profile(user), f"Your course {activity['courseCode']} {activity['Activity']} has a spot open! Act fast!")
                        # Finally, remove the activity from the database
                        self.database.remove_user_activity(user, activity["courseCode"], activity["Semester"], activity["Activity"])
                except InvalidActivityException:
                    continue
                except Exception as e:
                    # Ping techmaster04 if there is an error
                    # userID 516413751155621899
                    ibra = self.bot.get_user(516413751155621899)
                    await ibra.send(f"""Something went wrong while scraping. Here is the relevant information:
                    ```
                    User ID: {user}
                    Course code: {activity['courseCode']}
                    Activity: {activity['Activity']}
                    Semester: {activity['Semester']}
                    Error: {e}
                    ```""")
                    continue

    @nextcord.slash_command(name="uoft", description="Main command for all UofT related commands")
    async def uoft(self, interaction: Interaction):
        """
        Main command for all UofT related commands
        """
        pass

    @uoft.subcommand(name="track", description="Track a UofT course")
    async def track(self, interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to track. Example: CSC148H5"), activity: str = SlashOption(name="activity", description="The activity code which you want to track. Example: LEC0101"), session: str = SlashOption(
        name="semester",
        description="The semester in which the course is offered. Example: Fall",
        choices={"Fall": "F", "Winter": "S", "Full Year": "Y"},
    ),):
        course_code, activity = course_code.upper(), activity.upper()
        footer = "Thank you for using TTBTrackr"
        # Step One: Validate the course code/activity/semester 
        if not self.utils.validate_course(course_code, activity, session):
            await interaction.response.send_message("Invalid course code/activity/semester combination. Please try again.", ephemeral=True)
            return
        # Step Two: Validate whether or not the course exists in the UofT TTB Database. If it does not
        # Warn the user
        try:
            self.ttbapi.validate_course(course_code, session, activity)
        except CourseNotFoundException:
            await interaction.response.send_message("Invalid course code or semester. Please try again", ephemeral=True)
            return
        except InvalidActivityException:
            confirm = ConfirmDialogue()
            await interaction.response.send_message("The activity you entered is invalid for the course code selected. Would you like to track when this activity becomes availible? (i.e: New lecture/tutorial section added)", ephemeral=True, view=confirm)
            await confirm.wait()
            if not confirm.value:
                await interaction.followup.send("Cancelled", ephemeral=True)
                return
        # Step Three: Check if the user has a profile setup
        if not self.database.is_user_in_db(interaction.user.id):
            # Create a profile for the user, then set the embed footer as "Remember to setup your profile"
            self.database.add_user(interaction.user.id, {})
            footer = "Remember to setup your profile using /profile!"
        
        # Step 3.5: If the user DOES exist in the db, make sure their campus is set to UofT
        if not self.database.get_campus(interaction.user.id) == "UofT":
            await interaction.send("It looks like you have non-UofT courses being tracked. As of right now, you cannot track cross-campus courses.", ephemeral=True)
            return
        
        # If we're here, then the course is valid, and we can add it to the database
        # But first, we need to check if the course is already in the database
        if self.database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
            await interaction.send("You are already tracking this course/activity combination", ephemeral=True)
            return

        self.database.add_user_activity(
        interaction.user.id, course_code, session, activity)
        embed = nextcord.Embed(title="Course Added", description=f"Successfully added {course_code} {activity} to your tracked courses", color=nextcord.Color.blue())
        embed.set_footer(text=footer)
        # Finally, send a message congratulating the user on adding the course
        await interaction.send(embed=embed)

    @uoft.subcommand(name="untrack", description="Remove a UofT course from being tracked")
    async def untrack(self, interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to untrack. Example: CSC148H5"), activity: str = SlashOption(name="activity", description="The activity code which you want to untrack. Example: LEC0101"), session: str = SlashOption(
        name="semester",
        description="The semester in which the course is offered. Example: Fall",
        choices={"Fall": "F", "Winter": "S", "Full Year": "Y"},
    ),):
        if not self.database.is_user_in_db(interaction.user.id) or len(self.database.get_user_activities(interaction.user.id)) == 0:
            # If the user is not in the database or is not tracking any courses, send an error message
            embed = build_embed_from_json("Embeds/no_tracked_courses.json")
            await interaction.response.send_message(embed=embed)
            return
        course_code, activity = course_code.upper(), activity.upper()
        if not self.utils.validate_course(course_code, activity, session):
            # If the course code or activity code is invalid, send an error message
            await interaction.response.send_message("Invalid course code or activity code. Please try again.", ephemeral=True)
            return
        # Step 1: Check if the user is already tracking the course
        if not self.database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
            await interaction.response.send_message("You aren't tracking this course!", ephemeral=True)
            return
        # Step 2: Remove the course from the database
        self.database.remove_user_activity(
            interaction.user.id, course_code, session, activity)
        await interaction.response.send_message("Successfully removed the course from being tracked!", ephemeral=True)

    @uoft.subcommand(name="list", description="List all the courses you are tracking")
    async def view_tracked(self, interaction: nextcord.Interaction):
        if not self.database.is_user_in_db(interaction.user.id) or len(self.database.get_user_activities(interaction.user.id)) == 0:
            embed = build_embed_from_json("Embeds/no_tracked_courses.json")
            await interaction.response.send_message(embed=embed)
            return
        
        if not self.database.get_campus(interaction.user.id) == "UofT":
            await interaction.send("It looks like you don't have any UofT courses being tracked", ephemeral=True)
            return
        
        activities = self.database.get_user_activities(interaction.user.id)
        embed = nextcord.Embed(title="Tracked Courses",
                            description="Here are all the courses you're tracking", color=nextcord.Color.blue())
        for activity in activities:
            embed.add_field(name=f"{activity['courseCode']} {activity['Activity']} {activity['Semester']}",
                            value=self.ttbapi.get_name_from_code(activity['courseCode'], activity['Semester']), inline=False)
        await interaction.response.send_message(embed=embed)

class UofTUtils():
    """
    Class containing all utilities relevant to UofT courses
    """

    def __init__(self) -> None:
        pass

    def validate_course(self, course_code: str, activity: str, semester: str) -> bool:
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
