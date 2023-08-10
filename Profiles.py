# File containing the cog responsible for all profile-related commands.
from typing import Optional
import nextcord
from nextcord import SlashOption
from nextcord.ext import commands
from Mongo import Mongo
from CommonUtils import validate_phone_number, build_embed_from_json, sanitize_phone_number
from Buttons import ConfirmDialogue

class ProfilesCog(commands.Cog, name="Profiles"):
    def __init__(self, bot: commands.Bot, database: Mongo) -> None:
        super().__init__()
        self.bot = bot
        self.db = database
    
    @nextcord.slash_command(name="profile")
    async def profile(self, iteraction: nextcord.Interaction) -> None:
        """
        View your profile.
        """
        pass
    
    @profile.subcommand(name="edit", description="Setup or edit your profile")
    async def setup_profile(self, interaction: nextcord.Interaction, instagram_username: Optional[str] = SlashOption(name="instagram_username", description="The Instagram profile you want the bot to alert you on when vacancies are found"), cell_number: Optional[str] = SlashOption(name="cell_number", description="The cell-phone number you want the bot to text when vacancies are found")) -> None:
        user_id = interaction.user.id
        profile = {}
        if instagram_username:
            profile["instagram_username"] = instagram_username
        if cell_number:
            # validate the cell number
            if not validate_phone_number(cell_number):
                await interaction.response.send_message("Invalid phone number. Please try again. Note that this bot only supports Canadian phone numbers for SMS", ephemeral=True)
                return
            profile["phone_number"] = sanitize_phone_number(cell_number)
            
        if not self.db.is_user_in_db(user_id):
            self.db.add_user_to_db(user_id, profile)
            await interaction.response.send_message("Successfully setup your profile! Make sure to follow [@ttbtrackr](https://www.instagram.com/ttbtrackr/) on Instagram to get notified when we DM!", ephemeral=True)
        else:
            # User does not have a profile, create a new one.
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
        
        text_mappings = {"instagram_username": "Instagram Username", "phone_number": "Phone Number", "call": "Calling:"}
        
        # Add the user's discord profile picture
        embed.set_thumbnail(url=interaction.user.avatar.url)
        for key in profile:
            embed.add_field(name=text_mappings[key], value=profile[key], inline=False)
        embed.set_footer(text="You can edit your profile by using /profile edit")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @profile.subcommand(name="delete", description="Delete your profile")
    async def delete_profile(self, interaction: nextcord.Interaction) -> None:
        # First, check if the user has a profile
        if not self.db.is_user_in_db(interaction.user.id):
            await interaction.response.send_message("You don't have a profile to delete!", ephemeral=True)
        
        # For obvious reasons, we need to ask the user if they're sure
        confirm = ConfirmDialogue()
        message = await interaction.response.send_message(embed=build_embed_from_json("Embeds/delete_profile_warning.json"), ephemeral=True, view=confirm)
        await confirm.wait()
        if confirm.value:
            self.db.remove_user(interaction.user.id)
            await interaction.followup.send("Your profile has been deleted. We're sad to see you go 😢", ephemeral=True)
        else:
            await interaction.followup.send("Canceled", ephemeral=True)
