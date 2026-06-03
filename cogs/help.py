import discord
from discord.ext import commands
from discord import app_commands

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, is_admin: bool):
        self.bot = bot
        options = []
        if is_admin:
            options.extend([
                discord.SelectOption(label="Moderation", description="Kick, ban, timeout, warnings, role management", emoji="🛡️"),
                discord.SelectOption(label="Logging", description="Configure server event logging", emoji="📋"),
                discord.SelectOption(label="Sticky Messages", description="Manage persistent sticky messages", emoji="📌"),
                discord.SelectOption(label="Reaction Roles", description="Button and dropdown role panels", emoji="🎭"),
                discord.SelectOption(label="Welcome & Goodbye", description="Setup join/leave messages and cards", emoji="👋"),
                discord.SelectOption(label="Automod", description="Automatic word filtering", emoji="⚙️"),
            ])
        options.extend([
            discord.SelectOption(label="AFK", description="Set and manage your AFK status", emoji="💤")
        ])

        super().__init__(placeholder="Choose a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(title=category, color=discord.Color.blue())
        embed.set_footer(text="Serenity Assistant 2.0", icon_url=self.bot.user.display_avatar.url)

        if category == "Moderation":
            embed.description = (
                "**/lock** `[channel]`\n┗ Prevent members from sending messages in a channel\n\n"
                "**/unlock** `[channel]`\n┗ Re-allow messages in a locked channel\n\n"
                "**/purge** `<amount>`\n┗ Bulk delete messages in the current channel\n\n"
                "**/kick** `<member>` `[reason]`\n┗ Kick a member from the server\n\n"
                "**/ban** `<member>` `[reason]`\n┗ Permanently ban a member\n\n"
                "**/timeout** `<member>` `<minutes>` `[reason]`\n┗ Temporarily mute a member\n\n"
                "**/untimeout** `<member>`\n┗ Remove an active timeout\n\n"
                "**/warn** `<member>` `<reason>`\n┗ Issue a warning (logged to DB, DMs the user)\n\n"
                "**/warnings** `<member>`\n┗ View all warnings for a member\n\n"
                "**/clear_warnings** `<member>`\n┗ Wipe all warnings for a member\n\n"
                "**/role add** `<member>` `<role>`\n┗ Add a role to a member\n\n"
                "**/role remove** `<member>` `<role>`\n┗ Remove a role from a member\n\n"
                "**Setup:**\n"
                "```Make sure the bot's role is positioned ABOVE the\n"
                "roles it needs to manage in Server Settings > Roles.```"
            )

        elif category == "Automod":
            embed.description = (
                "**/automod add_banned_word** `<word>`\n┗ Add a word to the filter. Messages containing it will be auto-deleted\n\n"
                "**/automod remove_banned_word** `<word>`\n┗ Remove a word from the filter\n\n"
                "**How it works:**\n"
                "```When a message contains a banned word:\n"
                "  1. The message is immediately deleted\n"
                "  2. The user is DM'd with the matched word\n\n"
                "Tip: words are matched case-insensitively and\n"
                "as substrings (e.g. 'bad' matches 'badword').```"
            )

        elif category == "Sticky Messages":
            embed.description = (
                "**/sticky add** `[is_embed]`\n┗ Create or update the sticky in the current channel. `is_embed` toggles between embed and normal text.\n\n"
                "**/sticky remove**\n┗ Delete the sticky message from the current channel\n\n"
                "**/sticky enable**\n┗ Re-enable and re-post the sticky in this channel\n\n"
                "**/sticky disable**\n┗ Pause the sticky in this channel without deleting it\n\n"
                "**/sticky cooldown** `<messages>`\n┗ Set how many messages pass before re-posting (current channel)\n\n"
                "**/sticky list**\n┗ List all sticky messages active across the server\n\n"
                "**/sticky preview**\n┗ Preview the sticky for the current channel\n\n"
                "**Note:**\n"
                "```Each channel now supports exactly ONE sticky message.\n"
                "Commands automatically detect the sticky in your channel.```"
            )

        elif category == "Reaction Roles":
            embed.description = (
                "**/rr create** `<title>` `[description]` `[mode]` `[exclusive]`\n┗ Create a new role panel\n\n"
                "**/rr add_role** `<id>` `<role>` `[label]` `[emoji]` `[style]`\n┗ Add a role entry to a panel\n\n"
                "**/rr remove_role** `<id>` `<role>`\n┗ Remove a role from a panel\n\n"
                "**/rr post** `<id>` `[channel]`\n┗ Send the panel to a channel (run again to refresh)\n\n"
                "**/rr edit** `<id>` `[title]` `[description]` `[exclusive]`\n┗ Update a panel's settings\n\n"
                "**/rr list**\n┗ List all panels in the server\n\n"
                "**/rr delete** `<id>`\n┗ Delete a panel and its Discord message\n\n"
                "**Setup:**\n"
                "```1. /rr create <title> [mode: button/dropdown] [exclusive: true/false]\n"
                "2. /rr add_role <panel_id> <role> [label] [emoji] [style]\n"
                "3. /rr post <panel_id> [channel]```"
            )

        elif category == "Logging":
            embed.description = (
                "**/set_log_channel** `<type>` `<channel>`\n┗ Bind a channel to a specific log type\n\n"
                "**Log Types:**\n"
                "```messages, members, server, voice, roles, mod```\n"
                "**All logs are also saved to the SQLite database** for future web dashboard use."
            )

        elif category == "Welcome & Goodbye":
            embed.description = (
                "**/welcome set_channel** `<channel>`\n┗ Set the channel for welcome messages\n\n"
                "**/welcome set_goodbye_channel** `<channel>`\n┗ Set the channel for goodbye messages\n\n"
                "**/welcome set_message**\n┗ Modal to write the welcome message text\n\n"
                "**/welcome set_goodbye_message**\n┗ Modal to write the goodbye message text\n\n"
                "**/welcome set_background** `<image>`\n┗ Upload a custom image for welcome cards\n\n"
                "**/welcome set_goodbye_background** `<image>`\n┗ Upload a custom image for goodbye cards\n\n"
                "**/welcome reset_background** `<type>`\n┗ Reset background to the default gradient\n\n"
                "**/welcome preview** `<type>`\n┗ Preview the card and message\n\n"
                "**/welcome variables**\n┗ List all supported message variables\n\n"
                "**/welcome disable** `<type>`\n┗ Disable welcome or goodbye messages"
            )

        elif category == "AFK":
            embed.description = (
                "**/afk_set** `[reason]`\n┗ Mark yourself as AFK with an optional reason\n\n"
                "**/afk_clear**\n┗ Clear your AFK status manually\n\n"
                "**How it works:**\n"
                "```When you are AFK and someone mentions you, the bot\n"
                "will reply with your AFK reason.\n\n"
                "Clean Mode: All AFK-related notifications are\n"
                "automatically deleted after 5 seconds.\n\n"
                "Your AFK is automatically cleared the next time\n"
                "you send a message in any channel.```"
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
            description="Select a category from the dropdown below to view commands and setup guides.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Serenity Assistant 2.0", icon_url=self.bot.user.display_avatar.url)

        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        view = HelpView(self.bot, is_admin)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
