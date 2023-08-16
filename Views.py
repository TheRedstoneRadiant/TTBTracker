from __future__ import annotations
import nextcord
from Mongo import Mongo

class ConfirmDialogue(nextcord.ui.View):
    def init(self):
        super().__init__()
        self.value = None
    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.green)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = True
        self.stop()
    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.red)
    async def deny(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = False
        self.stop()

class NotificationToggleButton(nextcord.ui.Button):
    """
    Class which represents a button that toggles notifications on or off
    """
    
    def __init__(self, label: str, emoji: str, view: NotificationsView, index: int, menu: str, submenu: str) -> None:
        super().__init__(label=label, emoji=emoji, style=nextcord.ButtonStyle.green)
        self.view_object = view
        self.index = index
        self.menu = menu
        self.submenu = submenu

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await interaction.response.defer()
        embed = await self.view_object.update_embed(self.menu, self.submenu, self.label, self.index)
        await interaction.edit_original_message(embed=embed, view=self.view_object)

class NotificationsView(nextcord.ui.View):
    def __init__(self, user_id: int, embed: nextcord.embeds.Embed, db: Mongo, buttons: list[tuple[str, str, str, int]]) -> None:
        super().__init__()
        self.user_id = user_id
        self.embed = embed
        self.db = db
        for button in buttons:
            self.add_item(NotificationToggleButton(label=button[0], emoji=button[1], view=self,index=button[2], menu=button[3], submenu=button[4]))
    async def update_embed(self, menu: str, submenu: str, entry_name: str, index: int) -> nextcord.embeds.Embed:
        # Method which updates the database with the notification settings and 
        # Updates the embed with the new settings
        # Step one: Get the current profile
        profile = self.db.get_user_profile(self.user_id)
        # Step two: Get the current submenu setting
        current_submenu_setting = profile[menu][submenu]
        # Update the database with the new setting
        self.db.update_user_notifications(self.user_id, not current_submenu_setting, menu, submenu)
        # Update the embed with the new setting
        self.embed.set_field_at(index, name=entry_name[7:], value=f"On" if not current_submenu_setting else "Off", inline=True)
        return self.embed