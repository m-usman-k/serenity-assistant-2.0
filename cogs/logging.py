import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "database.sqlite"
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        # Ensure config table exists
        c.execute('''CREATE TABLE IF NOT EXISTS config 
                     (guild_id TEXT, key TEXT, value TEXT, 
                     PRIMARY KEY (guild_id, key))''')
        # Create table for actual logs (for the website UI)
        c.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     guild_id TEXT, log_type TEXT, description TEXT, timestamp TEXT)''')
        conn.commit()
        conn.close()

    def get_config(self, guild_id, key):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT value FROM config WHERE guild_id=? AND key=?", (str(guild_id), f"log_{key}"))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_config(self, guild_id, key, value):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (guild_id, key, value) VALUES (?, ?, ?)", (str(guild_id), f"log_{key}", str(value)))
        conn.commit()
        conn.close()

    def save_log_to_db(self, guild_id, log_type, description):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO logs (guild_id, log_type, description, timestamp) VALUES (?, ?, ?, ?)", 
                  (str(guild_id), log_type, description, timestamp))
        conn.commit()
        conn.close()

    def create_embed(self, title, description, color):
        return discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())

    async def send_log(self, guild, log_type, embed, raw_description=""):
        # Save to DB for website UI
        self.save_log_to_db(guild.id, log_type, raw_description or embed.description)
        
        # Send to Discord channel if configured
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
        await interaction.response.send_message(embed=self.create_embed("Logging Setup", f"{log_type.name} log channel set to {channel.mention}", discord.Color.green()))

    # --- Message Logging ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        desc = f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content or 'No text'}"
        embed = self.create_embed("🗑️ Message Deleted", desc, discord.Color.red())
        await self.send_log(message.guild, "messages", embed, f"Deleted by {message.author} in {message.channel.name}: {message.content}")

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages: return
        guild = messages[0].guild
        desc = f"**Channel:** {messages[0].channel.mention}\n**Amount:** {len(messages)} messages"
        embed = self.create_embed("🗑️ Bulk Messages Deleted", desc, discord.Color.red())
        await self.send_log(guild, "messages", embed, f"Bulk deleted {len(messages)} messages in {messages[0].channel.name}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content: return
        desc = f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content}\n**After:** {after.content}\n[Jump to message]({after.jump_url})"
        embed = self.create_embed("📝 Message Edited", desc, discord.Color.orange())
        await self.send_log(before.guild, "messages", embed, f"Edited by {before.author} in {before.channel.name}. Before: {before.content} | After: {after.content}")

    # --- Member Logging ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = self.create_embed("📥 Member Joined", f"{member.mention} ({member.id})", discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.send_log(member.guild, "members", embed, f"{member} joined the server")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = self.create_embed("📤 Member Left", f"{member.mention} ({member.id})", discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.send_log(member.guild, "members", embed, f"{member} left the server")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = self.create_embed("🔨 Member Banned", f"{user.mention} ({user.id})", discord.Color.dark_red())
        await self.send_log(guild, "mod", embed, f"{user} was banned from the server")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = self.create_embed("🔓 Member Unbanned", f"{user.mention} ({user.id})", discord.Color.green())
        await self.send_log(guild, "mod", embed, f"{user} was unbanned from the server")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            desc = f"**Member:** {after.mention}\n**Before:** {before.nick or before.name}\n**After:** {after.nick or after.name}"
            embed = self.create_embed("👤 Nickname Changed", desc, discord.Color.blue())
            await self.send_log(before.guild, "members", embed, f"{after} changed nickname from {before.nick} to {after.nick}")
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            if added or removed:
                desc = f"**Member:** {after.mention}\n"
                log_raw = f"{after}'s roles updated. "
                if added: 
                    desc += f"**Roles Added:** {', '.join(r.mention for r in added)}\n"
                    log_raw += f"Added: {[r.name for r in added]}. "
                if removed: 
                    desc += f"**Roles Removed:** {', '.join(r.mention for r in removed)}"
                    log_raw += f"Removed: {[r.name for r in removed]}."
                embed = self.create_embed("🎭 Roles Updated", desc, discord.Color.blue())
                await self.send_log(before.guild, "roles", embed, log_raw)

    # --- Role Logging ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = self.create_embed("➕ Role Created", f"**Role:** {role.mention}", discord.Color.green())
        await self.send_log(role.guild, "roles", embed, f"Role {role.name} created")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = self.create_embed("➖ Role Deleted", f"**Role:** {role.name}", discord.Color.red())
        await self.send_log(role.guild, "roles", embed, f"Role {role.name} deleted")

    # --- Voice Logging ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel is None and after.channel is not None:
            embed = self.create_embed("🎙️ Voice Joined", f"{member.mention} joined {after.channel.mention}", discord.Color.green())
            await self.send_log(member.guild, "voice", embed, f"{member} joined voice channel {after.channel.name}")
        elif before.channel is not None and after.channel is None:
            embed = self.create_embed("🚪 Voice Left", f"{member.mention} left {before.channel.mention}", discord.Color.red())
            await self.send_log(member.guild, "voice", embed, f"{member} left voice channel {before.channel.name}")
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            embed = self.create_embed("🔀 Voice Moved", f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}", discord.Color.blue())
            await self.send_log(member.guild, "voice", embed, f"{member} moved from {before.channel.name} to {after.channel.name}")

    # --- Server Logging ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = self.create_embed("📁 Channel Created", f"Channel {channel.mention} created.", discord.Color.green())
        await self.send_log(channel.guild, "server", embed, f"Channel {channel.name} created")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = self.create_embed("🗑️ Channel Deleted", f"Channel **{channel.name}** deleted.", discord.Color.red())
        await self.send_log(channel.guild, "server", embed, f"Channel {channel.name} deleted")

async def setup(bot):
    await bot.add_cog(Logging(bot))
