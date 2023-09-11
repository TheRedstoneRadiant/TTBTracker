from typing import Optional
import nextcord
from nextcord.ext import commands, application_checks
from Mongo import Mongo
from CommonUtils import validate_phone_number, build_embed_from_json, sanitize_phone_number
from Views import NotificationsView

class AdminCommands(commands.Cog):
    """
    Class which contains all the admin commands
    """
    def __init__(self, bot, db: Mongo):
        self.bot = bot
        self.db = db
    
    def check_if_it_is_me(interaction: nextcord.Interaction):
        return interaction.user.id == 516413751155621899
    
    @nextcord.slash_command(name="admin", description="Admin commands")
    # @application_checks.check(check_if_it_is_me)
    async def admin(self, interaction: nextcord.Interaction):
        pass
    
    @admin.subcommand(name="profile", description="Admin profile commands")
    # @application_checks.check(check_if_it_is_me)
    async def profile(self, interaction: nextcord.Interaction):
        pass
    
    @profile.subcommand(name="view", description="View a user's profile")
    @application_checks.check(check_if_it_is_me)
    async def view_profile(self, interaction: nextcord.Interaction, user: nextcord.Member):
        user_id = user.id
        
        if not self.db.is_user_in_db(user_id):
            await interaction.response.send_message(f"{user.mention} does not have a profile to view!", ephemeral=True)
            return
        
        profile = self.db.get_user_profile(user_id)
        embed = nextcord.Embed(title=f"{user.name}'s TTBTrackr Profile", description=f"Here is {user.name}'s profile information", color=nextcord.Color.blue())
        
        function_map = {"instagram": self._add_ig_to_profile, "phone_number": self._add_phone_to_profile}
        enabled_features = []
        # Add the user's discord profile picture
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Discord Username", value=f"{user.name}#{user.discriminator}", inline=False)
        for key in profile:
            enabled_features.extend(function_map.get(key, lambda arg1, arg2: None)(embed, profile))
        embed.set_footer(text="You can edit your profile by using /profile edit")
        view = NotificationsView(user_id, embed, self.db, enabled_features)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @profile.subcommand(name="delete", description="Delete a user's profile")
    @application_checks.check(check_if_it_is_me)
    async def delete_profile(self, interaction: nextcord.Interaction, user: nextcord.Member):
        """
        Delete a user's profile
        """
        if not self.db.is_user_in_db(user.id):
            await interaction.response.send_message(f"{user.mention} does not have a profile to delete!", ephemeral=True)
            return
        self.db.remove_user(user.id)
        await interaction.response.send_message(f"Successfully deleted {user.mention}'s profile", ephemeral=True)
    
    @profile.subcommand(name="edit", description="Forcibly edit a user's profile")
    @application_checks.check(check_if_it_is_me)
    async def edit_profile(self, interaction: nextcord.Interaction, user: nextcord.Member, instagram_username: Optional[str] = nextcord.SlashOption(name="instagram_username", description="The Instagram profile you want the bot to alert you on when vacancies are found"), cell_number: Optional[str] = nextcord.SlashOption(name="cell_number", description="The cell-phone number you want the bot to text when vacancies are found")):
        """
        Forcibly edit a user's profile
        """
        
        if not self.db.is_user_in_db(user.id):
            await interaction.response.send_message(f"{user.mention} does not have a profile to edit!", ephemeral=True)
            return
        profile = self.db.get_user_profile(user.id)
        if not instagram_username:
            profile.pop("instagram")
        if not cell_number:
            profile.pop("phone_number")
        
        if instagram_username:
            profile["instagram"]["username"] = instagram_username
            profile["instagram"]["enabled"] = True
        if cell_number:
            # validate the cell number
            if not validate_phone_number(cell_number):
                await interaction.response.send_message("Invalid phone number. Please try again. Note that this bot only supports Canadian phone numbers for SMS", ephemeral=True)
                return
            profile["phone_number"]["number"] = sanitize_phone_number(cell_number)
        self.db.update_user_profile(user.id, profile)
        await interaction.response.send_message(f"Successfully edited {user.mention}'s profile", ephemeral=True)
    
    @admin.subcommand(name="togglecalls", description="Toggls phone-call notifications for a user")
    @application_checks.check(check_if_it_is_me)
    async def enablephone(self, interaction: nextcord.Interaction, user: nextcord.Member):
        """
        toggles phone-call notifications for a user
        """
        if not self.db.is_user_in_db(user.id):
            await interaction.response.send_message(f"{user.mention} does not have a profile to edit!", ephemeral=True)
        # get the current profile
        profile = self.db.get_user_profile(user.id)
        profile["phone_number"]["call_notifications_activated"] = not profile["phone_number"]["call_notifications_activated"]
        self.db.update_user_profile(user.id, profile)
        await interaction.response.send_message(f"Successfully toggled phone-call notifications for {user.mention}. Current state: {profile['phone_number']['call_notifications_activated']}", ephemeral=True)
    
    @admin.subcommand(name="uoft", description="UofT admin commands")
    @application_checks.check(check_if_it_is_me)
    async def uoft(self, interaction: nextcord.Interaction):
        pass
    
    @uoft.subcommand(name="forceadd", description="Forcibly add an activity for a user to the database")
    @application_checks.check(check_if_it_is_me)
    async def forceadd(self, interaction: nextcord.Interaction, user: nextcord.Member, course_code: str, semester: str, activity: str):
        """
        Forcibly add an activity for a user to the database
        """
        if not self.db.is_user_in_db(user.id):
            await interaction.response.send_message(f"{user.mention} does not have a profile to add activities to!", ephemeral=True)
            return
        self.db.add_tracked_activity(user.id, course_code, semester, activity)
        await interaction.response.send_message(f"Successfully added {course_code} {semester} {activity} to {user.mention}'s profile", ephemeral=True)
    
    @uoft.subcommand(name="forceremove", description="Forcibly remove an activity for a user from the database")
    @application_checks.check(check_if_it_is_me)
    async def forceremove(self, interaction: nextcord.Interaction, user: nextcord.Member, course_code: str, semester: str, activity: str):
        """
        Forcibly remove an activity for a user from the database
        """
        if not self.db.is_user_in_db(user.id):
            await interaction.response.send_message(f"{user.mention} does not have a profile to remove activities from!", ephemeral=True)
            return
        self.db.remove_tracked_activity(user.id, course_code, semester, activity)
        await interaction.response.send_message(f"Successfully removed {course_code} {semester} {activity} from {user.mention}'s profile", ephemeral=True)


    def _add_ig_to_profile(self, embed: nextcord.embeds.Embed, profile_data: dict):
        embed.add_field(name="Instagram Username", value=f"[{profile_data['instagram']['username']}](https://instagram.com/{profile_data['instagram']['username']})", inline=False)
        embed.add_field(name="Instagram Notifications:", value="On" if profile_data["instagram"]["enabled"] else "Off", inline=False)
        return [("Toggle Instagram Notifications", "📸", len(embed.fields)-1, "instagram", "enabled")]
    
    def _add_phone_to_profile(self, embed: nextcord.embeds.Embed, profile_data: dict):
        embed.add_field(name="Phone Number", value=f'||{profile_data["phone_number"]["number"]}||', inline=False)
        embed.add_field(name="SMS Notifications:", value="On" if profile_data["phone_number"]["SMS"] else "Off", inline=False)
        to_return = [("Toggle SMS Notifications", "💬", len(embed.fields)-1, "phone_number", "SMS")]
        # Check to see if profile['phone_number']['call_notifications_active'] is true
        if profile_data["phone_number"]["call_notifications_activated"]:
            embed.add_field(name="Phonecall Notifications:", value="On" if profile_data["phone_number"]["call"] else "Off", inline=False)
            
            to_return.append(("Toggle Phonecall Notifications", "📞", len(embed.fields)-1, "phone_number", "call"))
        # embed.add_field(name="Phone Number Confirmed:", value="Yes" if profile_data["phone_number"]["confirmed"] else "No (You must confirm your number for phone-related notifications to activate)", inline=False)
        return to_return