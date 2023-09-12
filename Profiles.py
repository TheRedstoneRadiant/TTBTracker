# File containing the cog responsible for all profile-related commands.
from typing import Optional
import nextcord
from nextcord import SlashOption
from nextcord.ext import commands
from Mongo import Mongo
from CommonUtils import validate_phone_number, build_embed_from_json, sanitize_phone_number
from Views import ConfirmDialogue
from random import randint
from UserContact import UserContact
from Views import NotificationsView
import random

class ProfilesCog(commands.Cog, name="Profiles"):
    def __init__(self, bot: commands.Bot, database: Mongo, contact: UserContact) -> None:
        super().__init__()
        self.bot = bot
        self.db = database
        self.contact = contact
        self.version = "ProfileCore V3.2"
        
    @nextcord.slash_command(name="profile")
    async def profile(self, iteraction: nextcord.Interaction) -> None:
        """
        View your profile.
        """
        pass
    
    @profile.subcommand(name="edit", description="Setup or edit your profile")
    async def setup_profile(self, interaction: nextcord.Interaction, instagram_username: Optional[str] = SlashOption(name="instagram_username", description="The Instagram profile you want the bot to alert you on when vacancies are found"), cell_number: Optional[str] = SlashOption(name="cell_number", description="Your cell number. By providing your number, you consent to having it stored in TTBTrackr's database")) -> None:
        user_id = interaction.user.id
        
        profile = {
            "instagram": {"username": "", "enabled": False},
            "phone_number": {"number": "", "SMS": True, "call": False, "confirmed": False, "call_notifications_activated": False}
        }
        
        if self.db.is_user_in_db(user_id) and self.db.get_user_profile(user_id):
            profile = self.db.get_user_profile(user_id)
        else:
            faults = self.db.get_user_faults(user_id)
            profile['phone_number'].update(faults)
        
        # If the instagram parameter isn't specified, remove it from the profile
        if not instagram_username and "instagram" in profile:
            profile.pop("instagram")
        if not cell_number and "phone_number" in profile:
            profile.pop("phone_number")
        
        if instagram_username:
            profile["instagram"]["username"] = instagram_username
            profile["instagram"]["enabled"] = True
        if cell_number:
            failed_attempts = profile['phone_number'].get("failed_attempts", 0) + 1
            if failed_attempts % 6 == 0:
                await interaction.response.send_message("Phone related features have been disabled on this account. Please contact support for further instructions", ephemeral=True)
                return
            # validate the cell number
            if not validate_phone_number(cell_number):
                await interaction.response.send_message("Invalid phone number. Please try again. Note that this bot only supports Canadian phone numbers for SMS", ephemeral=True)
                return
            profile["phone_number"]["number"] = sanitize_phone_number(cell_number)
            profile['phone_number']['code'] = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            self.contact.confirm_user_number(profile["phone_number"]["number"], profile['phone_number']['code'])
            
        if not self.db.is_user_in_db(user_id):
            self.db.add_user_to_db(user_id, profile)
            await interaction.response.send_message("Successfully setup your profile! Make sure to follow [@ttbtrackr](https://www.instagram.com/ttbtrackr/) on Instagram and add (850) - 660 - 0835 to get notified when we send a message!", ephemeral=True)
        else:
            self.db.update_user_profile(user_id, profile)
            await interaction.response.send_message("Your profile has been updated!", ephemeral=True)
        
    @profile.subcommand(name="view", description="View your profile")
    async def view_profile(self, interaction: nextcord.Interaction):
        user_id = interaction.user.id
        if not self.db.is_user_in_db(user_id):
            await interaction.response.send_message("You don't have a profile to view!", ephemeral=True)
            return
        profile = self.db.get_user_profile(user_id)
        embed = nextcord.Embed(title="Your TTBTrackr Profile", description="Here is your profile information", color=nextcord.Color.blue())
        
        function_map = {"instagram": self._add_ig_to_profile, "phone_number": self._add_phone_to_profile}
        enabled_features = []
        # Add the user's discord profile picture
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.add_field(name="Discord Username", value=f"{interaction.user.name}#{interaction.user.discriminator}", inline=False)
        for key in profile:
            enabled_features.extend(function_map.get(key, lambda arg1, arg2: None)(embed, profile))
        embed.set_footer(text="You can edit your profile by using /profile edit")
        view = NotificationsView(user_id, embed, self.db, enabled_features)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
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
        embed.add_field(name="Phone Number Confirmed:", value="Yes" if profile_data["phone_number"]["confirmed"] else "No **(You must confirm your number for phone-related notifications to activate)**", inline=False)
        return to_return
        
    @profile.subcommand(name="delete", description="Delete your profile")
    async def delete_profile(self, interaction: nextcord.Interaction) -> None:
        # First, check if the user has a profile
        if not self.db.is_user_in_db(interaction.user.id):
            await interaction.response.send_message("You don't have a profile to delete!", ephemeral=True)
            return
        # For obvious reasons, we need to ask the user if they're sure
        confirm = ConfirmDialogue()
        await interaction.response.send_message(embed=build_embed_from_json("Embeds/delete_profile_warning.json"), ephemeral=True, view=confirm)
        await confirm.wait()
        if confirm.value:
            self.db.remove_user(interaction.user.id)
            await interaction.followup.send("Your profile has been deleted. We're sad to see you go 😢", ephemeral=True)
        else:
            await interaction.followup.send("Canceled", ephemeral=True)

    @profile.subcommand(name="confirm", description="Verify your phone number to activate phone-related functions")
    async def verify(self, interaction: nextcord.Interaction, code: str):
        if not self.db.is_user_in_db(interaction.user.id):
            await interaction.response.send_message("You don't have a profile setup. Use `/profile edit` to setup your profile!", ephemeral=True)
            return
        
        user_profile = self.db.get_user_profile(interaction.user.id)
        if user_profile['phone_number']['confirmed']:
            await interaction.response.send_message("You already confirmed your number", ephemeral=True)
            return
        
        if code == user_profile['phone_number']['code']:
            await interaction.response.send_message("Phone number successfully confirmed!", ephemeral=True)
            user_profile['phone_number']['confirmed'] = True
            self.db.update_user_profile(interaction.user.id, user_profile)
            return

        failed_attempts = user_profile['phone_number'].get("failed_attempts", 0) + 1
        user_profile['phone_number']['failed_attempts'] = failed_attempts
        if failed_attempts % 6 == 0:
            await interaction.response.send_message("Phone-related features have been disabled on this account. Please contact support for further instructions", ephemeral=True)
            return
        if failed_attempts % 3 == 0:
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            user_profile['phone_number']['code'] = code
            self.db.update_user_profile(interaction.user.id, user_profile)
            self.db.update_user_faults(interaction.user.id, {"failed_attempts": failed_attempts})
            self.contact.confirm_user_number(user_profile["phone_number"]["number"], code)
            await interaction.response.send_message("Verification failed. A new verification code has been sent.", ephemeral=True)        
            return

        await interaction.response.send_message("Invalid code, please try again", ephemeral=True)
        self.db.update_user_profile(interaction.user.id, user_profile)
        self.db.update_user_faults(interaction.user.id, {"failed_attempts": failed_attempts})

    
    @profile.subcommand(name="resend", description="Resend your verification code, if you didn't recieve it")
    async def resend(self, interaction: nextcord.Interaction):
        if not self.db.is_user_in_db(interaction.user.id):
            await interaction.response.send_message("You don't have a profile setup. Use `/profile edit` to setup your profile!", ephemeral=True)
            return
        
        user_profile = self.db.get_user_profile(interaction.user.id)
        if user_profile['phone_number']['confirmed']:
            await interaction.response.send_message("You already confirmed your number", ephemeral=True)
            return

        resent_codes = user_profile['phone_number'].get("failed_attempts", 0) + 1
        user_profile['phone_number']['failed_attempts'] = resent_codes
        if resent_codes % 6 == 0:
            await interaction.response.send_message("Phone-related features have been disabled on this account. Please contact support for further instructions", ephemeral=True)
            #TODO: Disable the SMS and Phone functions here
            return
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        user_profile['phone_number']['code'] = code
        self.db.update_user_profile(interaction.user.id, user_profile)
        self.contact.confirm_user_number(user_profile["phone_number"]["number"], code)
        self.db.update_user_faults(interaction.user.id, {"failed_attempts": resent_codes})
        await interaction.response.send_message("Verification code resent!", ephemeral=True)