import discord
from discord.ext import commands
from discord import app_commands

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, is_admin: bool):
        self.bot = bot
        options = []
        if is_admin:
            options.extend([
                discord.SelectOption(label="Moderation Commands", description="Commands for managing the server (Admin)", emoji="🛡️"),
                discord.SelectOption(label="Logging Commands", description="Configure server logging (Admin)", emoji="📋"),
                discord.SelectOption(label="Utility Commands", description="Useful utility commands (Admin)", emoji="🛠️"),
                discord.SelectOption(label="Welcome & Goodbye", description="Setup welcome/goodbye (Admin)", emoji="👋"),
                discord.SelectOption(label="Automod & Admin Economy", description="Automod and economy admin", emoji="⚙️"),
            ])
        options.extend([
            discord.SelectOption(label="Leveling Commands", description="XP and Leveling system", emoji="📈"),
            discord.SelectOption(label="Economy Commands", description="Money and economy system", emoji="💰"),
            discord.SelectOption(label="AFK Commands", description="Set and clear AFK status", emoji="💤")
        ])
        
        super().__init__(placeholder="Choose a category to view commands...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(title=category, color=discord.Color.blue())
        embed.set_footer(text="The Urbex Factory | Modern Urbex Community", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")

        if category == "Moderation Commands":
            embed.description = (
                "**/lock**\n┗ Lock a channel\n\n"
                "**/unlock**\n┗ Unlock a channel\n\n"
                "**/purge**\n┗ Purge messages in a channel\n\n"
                "**/kick**\n┗ Kick a member from the server\n\n"
                "**/ban**\n┗ Ban a member from the server\n\n"
                "**/timeout**\n┗ Timeout a member\n\n"
                "**/untimeout**\n┗ Remove timeout from a member\n\n"
                "**/warn**\n┗ Issue a warning to a member\n\n"
                "**/warnings**\n┗ Check a member's warnings\n\n"
                "**/clear_warnings**\n┗ Clear all warnings for a member\n\n"
                "**/role add**\n┗ Add a role to a user\n\n"
                "**/role remove**\n┗ Remove a role from a user\n\n"
                "**How to Setup Moderation:**\n"
                "`Moderation commands work automatically based on Discord permissions. Make sure the bot's role is higher than the roles it is trying to manage!`"
            )
        elif category == "Automod & Admin Economy":
            embed.description = (
                "**/automod add_banned_word**\n┗ Add a word to the banned words filter\n\n"
                "**/automod remove_banned_word**\n┗ Remove a word from the filter\n\n"
                "**/economy_admin add_money**\n┗ Add money to a user's balance\n\n"
                "**/economy_admin remove_money**\n┗ Remove money from a user's balance\n\n"
                "**How to Setup Automod:**\n"
                "`Use /automod add_banned_word <word> to start filtering bad words. The bot will automatically delete messages containing these words and DM the user.`"
            )
        elif category == "Utility Commands":
            embed.description = (
                "**/sticky_add**\n┗ Set a sticky message for this channel\n\n"
                "**/sticky_remove**\n┗ Remove the sticky message from this channel\n\n"
                "**/reaction_role**\n┗ Set up a button reaction role\n\n"
                "**How to Setup Reaction Roles:**\n"
                "`Use /reaction_role <role> <message> to create a button that users can click to get or remove a specific role.`"
            )
        elif category == "AFK Commands":
            embed.description = (
                "**/afk_set**\n┗ Set your AFK status\n\n"
                "**/afk_clear**\n┗ Clear your AFK status\n\n"
            )
        elif category == "Logging Commands":
            embed.description = (
                "**/set_log_channel**\n┗ Set the channel for specific logging types\n\n"
                "**How to Setup Logging:**\n"
                "`Use /set_log_channel to bind channels to different events. You can set channels for 'Messages' (edits/deletes), 'Members' (joins/leaves), 'Server' (channel creates/deletes), 'Voice' (joins/moves), 'Roles', and 'Moderation' (bans/kicks).`"
            )
        elif category == "Leveling Commands":
            embed.description = (
                "**/rank**\n┗ Check your or someone else's current level and XP\n\n"
                "**/leaderboard**\n┗ View the top members with the most XP\n\n"
                "**/leveling_setup set_channel** (Admin)\n┗ Set the channel for level up messages\n\n"
                "**How to Setup Leveling:**\n"
                "`Users automatically earn random XP between 15 and 25 per message. Use /leveling_setup set_channel <channel> to define where level up notifications should be sent. If not set, it sends in the current channel.`"
            )
        elif category == "Economy Commands":
            embed.description = (
                "**/balance**\n┗ Check your or someone else's wallet balance\n\n"
                "**/work**\n┗ Work to earn some coins (1 hour cooldown)\n\n"
                "**/pay**\n┗ Pay coins to another user\n\n"
                "**How to Setup Economy:**\n"
                "`Economy requires no setup. Users can immediately use /work to start earning coins. Admins can manage balances using /economy_admin commands.`"
            )
        elif category == "Welcome & Goodbye":
            embed.description = (
                "**/welcome_setup set_channel**\n┗ Set the channel for welcome messages\n\n"
                "**/welcome_setup set_message**\n┗ Customize the welcome message text\n\n"
                "**/welcome_setup set_goodbye_channel**\n┗ Set the channel for goodbye messages\n\n"
                "**How to Setup Welcome Messages:**\n"
                "`1. Use /welcome_setup set_channel <channel>`\n"
                "`2. Use /welcome_setup set_message <message>`\n"
                "`Supported variables for message: {user.mention}, {user.name}, {server}`"
            )

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, is_admin: bool):
        super().__init__()
        self.add_item(HelpSelect(bot, is_admin))

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show the bot's help menu")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Help Menu",
            description="Please select a category from the dropdown below to view its commands.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="The Urbex Factory | Modern Urbex Community", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
        
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        view = HelpView(self.bot, is_admin)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
