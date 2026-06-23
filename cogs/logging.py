import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
from datetime import datetime

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_connection(self):
        return self.bot.db.get_connection()

    def get_config(self, guild_id, key):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT config_value FROM serenity_config WHERE guild_id=%s AND config_key=%s", (str(guild_id), f"log_{key}"))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_config(self, guild_id, key, value):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("REPLACE INTO serenity_config (guild_id, config_key, config_value) VALUES (%s, %s, %s)", (str(guild_id), f"log_{key}", str(value)))
        conn.commit()
        conn.close()

    def save_log_to_db(self, guild_id, log_type, description):
        conn = self.get_connection()
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO serenity_logs (guild_id, log_type, description, timestamp) VALUES (%s, %s, %s, %s)", 
                  (str(guild_id), log_type, description, timestamp))
        conn.commit()
        conn.close()

    def create_base_embed(self, color, user: discord.Member | discord.User = None):
        embed = discord.Embed(color=color, timestamp=datetime.now())
        if user:
            embed.set_author(name=f"{user}", icon_url=user.display_avatar.url)
        return embed

    async def send_log(self, guild, log_type, embed, raw_description=""):
        self.save_log_to_db(guild.id, log_type, raw_description or embed.description or embed.title or "No description")
        channel_id = self.get_config(guild.id, log_type)
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                try:
                    await channel.send(embed=embed)
                except:
                    pass

    @app_commands.command(name="set_log_channel", description="Set a log channel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(log_type=[
        app_commands.Choice(name="Messages", value="messages"),
        app_commands.Choice(name="Members", value="members"),
        app_commands.Choice(name="Server", value="server"),
        app_commands.Choice(name="Voice", value="voice"),
        app_commands.Choice(name="Roles", value="roles"),
        app_commands.Choice(name="Moderation", value="mod")
    ])
    async def set_log_channel(self, interaction: discord.Interaction, log_type: app_commands.Choice[str], channel: discord.TextChannel):
        self.set_config(interaction.guild_id, log_type.value, channel.id)
        embed = self.create_base_embed(discord.Color.green(), interaction.user)
        embed.title = "Logging Setup"
        embed.description = f"Log channel for `{log_type.name}` set to {channel.mention}"
        await interaction.response.send_message(embed=embed)

    # --- Message Logging ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        embed = self.create_base_embed(discord.Color.red(), message.author)
        embed.title = f"Message deleted in #{message.channel.name}"
        # We don't have a jump URL for deleted messages, so we use a safe fallback or nothing
        embed.description = f"**Content:**\n{message.content or 'No content'}"
        embed.set_footer(text=f"ID: {message.author.id}")
        await self.send_log(message.guild, "messages", embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages: return
        guild = messages[0].guild
        embed = self.create_base_embed(discord.Color.red())
        embed.title = f"Bulk Message Deletion in #{messages[0].channel.name}"
        embed.description = f"**Amount:** `{len(messages)}` messages"
        await self.send_log(guild, "messages", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content: return
        embed = self.create_base_embed(discord.Color.blue(), before.author)
        # Applying the "link" style to the title
        embed.title = f"Message edited in #{before.channel.name}"
        embed.url = after.jump_url 
        embed.description = (
            f"**Before:** {before.content}\n"
            f"**After:** {after.content}"
        )
        embed.set_footer(text=f"ID: {before.author.id}")
        await self.send_log(before.guild, "messages", embed)

    # --- Member Logging ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = self.create_base_embed(discord.Color.green(), member)
        embed.title = "Member Joined"
        embed.description = f"**Account Created:** <t:{int(member.created_at.timestamp())}:R>"
        embed.set_footer(text=f"ID: {member.id}")
        await self.send_log(member.guild, "members", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = self.create_base_embed(discord.Color.red(), member)
        embed.title = "Member Left"
        embed.set_footer(text=f"ID: {member.id}")
        await self.send_log(member.guild, "members", embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = self.create_base_embed(discord.Color.dark_red(), user)
        embed.title = "Member Banned"
        embed.set_footer(text=f"ID: {user.id}")
        await self.send_log(guild, "mod", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = self.create_base_embed(discord.Color.green(), user)
        embed.title = "Member Unbanned"
        embed.set_footer(text=f"ID: {user.id}")
        await self.send_log(guild, "mod", embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            embed = self.create_base_embed(discord.Color.blue(), after)
            embed.title = "Nickname Changed"
            embed.description = f"**Before:** `{before.nick or before.name}`\n**After:** `{after.nick or after.name}`"
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(before.guild, "members", embed)
            
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            if added or removed:
                embed = self.create_base_embed(discord.Color.blue(), after)
                embed.title = "Roles Updated"
                if added: embed.add_field(name="Roles Added", value=", ".join(r.mention for r in added), inline=False)
                if removed: embed.add_field(name="Roles Removed", value=", ".join(r.mention for r in removed), inline=False)
                embed.set_footer(text=f"ID: {after.id}")
                await self.send_log(before.guild, "roles", embed)

        if before.timed_out_until != after.timed_out_until:
            embed = self.create_base_embed(discord.Color.orange(), after)
            if after.timed_out_until:
                embed.title = "Member Timed Out"
                embed.description = f"**Until:** <t:{int(after.timed_out_until.timestamp())}:f>"
            else:
                embed.title = "Timeout Removed"
                embed.description = "**Status:** Timeout removed."
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(before.guild, "mod", embed)

    # --- Role Logging ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = self.create_base_embed(discord.Color.green())
        embed.title = f"Role Created: `{role.name}`"
        embed.set_footer(text=f"ID: {role.id}")
        await self.send_log(role.guild, "roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = self.create_base_embed(discord.Color.red())
        embed.title = f"Role Deleted: `{role.name}`"
        embed.set_footer(text=f"ID: {role.id}")
        await self.send_log(role.guild, "roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name != after.name or before.color != after.color:
            embed = self.create_base_embed(discord.Color.blue())
            embed.title = f"Role Updated: `{after.name}`"
            if before.name != after.name:
                embed.add_field(name="Old Name", value=f"`{before.name}`", inline=True)
                embed.add_field(name="New Name", value=f"`{after.name}`", inline=True)
            if before.color != after.color:
                embed.add_field(name="Old Color", value=f"`{before.color}`", inline=True)
                embed.add_field(name="New Color", value=f"`{after.color}`", inline=True)
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(before.guild, "roles", embed)

    # --- Voice Logging ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel is None and after.channel is not None:
            embed = self.create_base_embed(discord.Color.green(), member)
            embed.title = "Voice Joined"
            embed.description = f"**Channel:** {after.channel.mention}"
            embed.set_footer(text=f"ID: {member.id}")
            await self.send_log(member.guild, "voice", embed)
        elif before.channel is not None and after.channel is None:
            embed = self.create_base_embed(discord.Color.red(), member)
            embed.title = "Voice Left"
            embed.description = f"**Channel:** {before.channel.mention}"
            embed.set_footer(text=f"ID: {member.id}")
            await self.send_log(member.guild, "voice", embed)
        elif before.channel and after.channel and before.channel.id != after.channel.id:
            embed = self.create_base_embed(discord.Color.blue(), member)
            embed.title = "Voice Moved"
            embed.description = f"**From:** {before.channel.mention}\n**To:** {after.channel.mention}"
            embed.set_footer(text=f"ID: {member.id}")
            await self.send_log(member.guild, "voice", embed)

    # --- Server/Channel Logging ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = self.create_base_embed(discord.Color.green())
        embed.title = f"Channel Created: `{channel.name}`"
        embed.description = f"**Type:** `{channel.type}`"
        embed.set_footer(text=f"ID: {channel.id}")
        await self.send_log(channel.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = self.create_base_embed(discord.Color.red())
        embed.title = f"Channel Deleted: `{channel.name}`"
        embed.set_footer(text=f"ID: {channel.id}")
        await self.send_log(channel.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name != after.name:
            embed = self.create_base_embed(discord.Color.blue())
            embed.title = f"Channel Renamed: `{after.name}`"
            embed.description = f"**Old Name:** `{before.name}`"
            embed.set_footer(text=f"ID: {after.id}")
            await self.send_log(before.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.name != after.name:
            embed = self.create_base_embed(discord.Color.blue())
            embed.title = "Server Renamed"
            embed.description = f"**Old Name:** `{before.name}`\n**New Name:** `{after.name}`"
            embed.set_footer(text=f"Guild ID: {after.id}")
            await self.send_log(before, "server", embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
