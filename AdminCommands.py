import nextcord
from nextcord.ext import commands


class AdminCommands(commands.Cog):
    """
    Class which contains all the admin commands
    """
    def __init__(self, bot):
        self.bot = bot
