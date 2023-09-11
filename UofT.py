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
from CommonUtils import *
from UserContact import UserContact
from Courses import Course, Activity


class UofT(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Mongo, contact: UserContact) -> None:
        self.bot = bot
        self.ttbapi = TTBAPI()
        self.utils = UofTUtils()
        self.database = database
        self.contact = contact
        self.refresh.start()

    @tasks.loop(seconds=30)
    async def refresh(self) -> None:
        """
        Method which actively checks the UofT API for changes in course status.
        And notifies users when their desired course is availible
        """
        await self.bot.wait_until_ready()
        # Get a list of all the courses in the database
        courses = self.database.get_all_courses()
        for course in courses:
            course_object = self.ttbapi.get_course(
                course["course_code"], course["semester"])
            for activity in course['activities']:
                if "New" in activity:
                    # If this activity is checking for new sections being opened
                    await self.check_for_new_sections(course, activity)
                    continue
                activity_object = course_object.get_activity(activity)
                if activity_object.is_seats_free():
                    # If an activity has seats free, then we need to notify the users
                    message = f"Seats are availible for {course['course_code']} - {course_object.get_name()}, {self._format_activity(activity)}, in {self._format_semester(course['semester'])}"
                    await self._contact_users(course["activities"][activity], course["course_code"], course["semester"], activity, message)

    def _format_activity(self, activity: str):
        activity_map = {"LEC": "Lecture", "TUT": "Tutorial", "PRA": "Practical"}
        activity = activity.upper()
        activity = activity_map.get(activity[:3], None) + " " + activity[3:]
        if not activity:
            activity = "new " + activity_map.get(activity[3:], None)
        
        return activity
    
    def _format_semester(self, semester: str):
        mapping = {"F": "Fall", "S": "Winter", "Y": "Full Year"}
        return mapping[semester]

    async def check_for_new_sections(self, course: dict, activity: str) -> None:
        course_code = course["course_code"]
        semester = course["semester"]
        # Get the current course sections
        course_object = self.ttbapi.get_course(course_code, semester)
        activities = course_object.get_activity_by_type(activity[3:])
        # sort the activities by their section number
        activities.sort()
        if not self.database.is_course_sections_in_database(course_code, semester, activity[3:]):
            self.database.add_course_sections(
                course_code, semester, activity[3:], activities)
            return
        # If the course has been added to the database, then we need to check if there are any new sections
        # Get teh sections from the database
        current_sections = self.database.get_course_sections(
            course_code, semester, activity[3:])
        # We can convert the two lists into sets and then find the difference between them
        # If we have a difference, then we need to notify the users
        # This is useful because it can tell us what the new lecture code is
        new_sections = set(activities) - set(current_sections)
        if new_sections:
            # Get all the people tracking new sections for this course
            users = course["activities"][activity]
            word_mappings = {"NewLEC": "lectures",
                             "NewTUT": "tutorials", "NewPRA": "practicals"}
            message = f"New sections have been opened for {course_code} {word_mappings[activity]} in {semester}: {', '.join(list(new_sections))}"
            await self._contact_users(users, course_code, semester, activity, message)
            # Update the database with the new sections
            self.database.add_course_sections(
                course_code, semester, activity[3:], activities)

    async def _contact_users(self, users: list[int], coursecode: str, semester: str, activity: str, message: str) -> None:
        """
        Method which contacts all users in the given list
        """
        for user in users:
            # Step 1: contact via discord
            discord_user = self.bot.get_user(user)
            await discord_user.send(message)
            self.contact.contact_user(
                self.database.get_user_profile(user), message)
            # Remove the user from the database
            self.database.remove_tracked_activity(
                user, coursecode, semester, activity)

    @nextcord.slash_command(name="uoft", description="Main command for all UofT related commands")
    async def uoft(self, interaction: Interaction):
        """
        Main command for all UofT related commands
        """
        pass

    @uoft.subcommand(name="track", description="Track a UofT course")
    async def track(self, interaction: nextcord.Interaction):
        pass

    @track.subcommand(name="new", description="Track new activity sections being opened")
    async def new_section(self, interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to track. Example: CSC148H5"), session: str = SlashOption(description="The semester in which the course is offered. Example: Fall", choices={"Fall": "F", "Winter": "S", "Full Year": "Y"}), activity: str = SlashOption(description="The new activity section you want to track", choices=["LEC", "TUT", "PRA"])):
        course_code, activity = course_code.upper(), activity.upper()
        footer = "Thank you for using TTBTrackr"
        # Step One: Validate the course code/activity/semester
        if not self.utils.validate_course(course_code, f"{activity}0000", session):
            await interaction.response.send_message("Invalid course code/activity/semester combination. Please try again.", ephemeral=True)
            return
        try:
            self.ttbapi.validate_course(course_code, session, activity)
        except CourseNotFoundException:
            # If the course is not found, it's invalid
            await interaction.response.send_message("Invalid course code or semester. Please try again", ephemeral=True)
            return
        except InvalidActivityException:
            # If we get InvalidActivityException - that's the point. The activity will be invalid
            # Since it's just LEC/PRA/TUT. This is fine because we'll deal with it
            # In the scraping function
            pass
        if not self.database.is_user_in_db(interaction.user.id):
            # Create a profile for the user, then set the embed footer as "Remember to setup your profile"
            self.database.add_user_to_db(interaction.user.id, {})
            footer = "Remember to setup your profile using /profile!"

        # If we're here, then the course is valid, and we can add it to the database
        # But first, we need to check if the course is already in the database
        if self.database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
            await interaction.send("You are already tracking this course/activity combination", ephemeral=True)
            return
        self.database.add_tracked_activity(
            interaction.user.id, course_code, session, f"New{activity}")
        embed = nextcord.Embed(
            title="Course Added", description=f"Successfully added {course_code} {activity} to your tracked courses", color=nextcord.Color.blue())
        embed.set_footer(text=footer)
        # Finally, send a message congratulating the user on adding the course
        await interaction.send(embed=embed)

    @track.subcommand(name="existing", description="Track an existing course activity")
    async def activity(self, interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to track. Make sure to include the campus code (ex: H5)!"), activity: str = SlashOption(name="activity", description="The activity code which you want to track. Example: LEC0101"), session: str = SlashOption(
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
            await interaction.response.send_message("Hmm.. Looks like that activity is invalid for that course/semester combo. Please check those and try again. If you're trying to track new sections being opened, use `/uoft track new` instead", ephemeral=True)
            return
        # Step Three: Check if the user has a profile setup
        if not self.database.is_user_in_db(interaction.user.id):
            # Create a profile for the user, then set the embed footer as "Remember to setup your profile"
            self.database.add_user_to_db(interaction.user.id, {})
            footer = "Remember to setup your profile using /profile!"

        # If we're here, then the course is valid, and we can add it to the database
        # But first, we need to check if the course is already in the database
        if self.database.is_user_tracking_activity(interaction.user.id, course_code, session, activity):
            await interaction.send("You are already tracking this course/activity combination", ephemeral=True)
            return

        self.database.add_tracked_activity(
            interaction.user.id, course_code, session, activity)
        embed = nextcord.Embed(
            title="Course Added", description=f"Successfully added {course_code} {activity} to your tracked courses", color=nextcord.Color.blue())
        embed.set_footer(text=footer)
        # Finally, send a message congratulating the user on adding the course
        await interaction.send(embed=embed)

    @uoft.subcommand(name="untrack", description="Remove a UofT course from being tracked")
    async def untrack(self, interaction: nextcord.Interaction, course_code: str = SlashOption(name="course_code", description="The course code of the course you want to untrack. Example: CSC148H5"), activity: str = SlashOption(name="activity", description="The activity code which you want to untrack. Example: LEC0101"), session: str = SlashOption(
        name="semester",
        description="The semester in which the course is offered. Example: Fall",
        choices={"Fall": "F", "Winter": "S", "Full Year": "Y"},
    ),):
        if not self.database.is_user_in_db(interaction.user.id) or len(self.database.get_user_tracked_activities(interaction.user.id)) == 0:
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
        self.database.remove_tracked_activity(
            interaction.user.id, course_code, session, activity)
        await interaction.response.send_message("Successfully removed the course from being tracked!", ephemeral=True)

    @uoft.subcommand(name="list", description="List all the courses you are tracking")
    async def view_tracked(self, interaction: nextcord.Interaction):
        if not self.database.is_user_in_db(interaction.user.id) or len(self.database.get_user_tracked_activities(interaction.user.id)) == 0:
            embed = build_embed_from_json("Embeds/no_tracked_courses.json")
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.defer()
        activities = self.database.get_user_tracked_activities(
            interaction.user.id)
        embed = nextcord.Embed(title="Tracked Courses",
                               description="Here are all the courses you're tracking", color=nextcord.Color.blue())
        for activity in activities:
            embed.add_field(name=f"{activity['coursecode']} {activity['activity']} {activity['semester']}", value=self.ttbapi.get_course(
                activity['coursecode'], activity['semester']).name, inline=False)

        await interaction.followup.send(embed=embed)


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
