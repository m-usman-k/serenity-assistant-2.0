import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import timedelta, datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "database.sqlite"
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS warnings 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     guild_id TEXT, user_id TEXT, moderator_id TEXT, reason TEXT, timestamp TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS automod 
                     (guild_id TEXT, word TEXT, 
                     PRIMARY KEY (guild_id, word))''')
        conn.commit()
        conn.close()

    def add_warning(self, guild_id, user_id, moderator_id, reason):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)", 
                  (str(guild_id), str(user_id), str(moderator_id), reason, timestamp))
        conn.commit()
        conn.close()

    def get_warnings(self, guild_id, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT moderator_id, reason, timestamp FROM warnings WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id)))
        results = [{"moderator": row[0], "reason": row[1], "timestamp": row[2]} for row in c.fetchall()]
        conn.close()
        return results

    def clear_user_warnings(self, guild_id, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (str(guild_id), str(user_id)))
        conn.commit()
        conn.close()

    def get_banned_words(self, guild_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT word FROM automod WHERE guild_id=?", (str(guild_id),))
        results = [row[0] for row in c.fetchall()]
        conn.close()
        return results

    def add_banned_word(self, guild_id, word):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO automod (guild_id, word) VALUES (?, ?)", (str(guild_id), word.lower()))
        conn.commit()
        conn.close()

    def remove_banned_word(self, guild_id, word):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("DELETE FROM automod WHERE guild_id=? AND word=?", (str(guild_id), word.lower()))
        conn.commit()
        conn.close()

    def create_embed(self, description, color=discord.Color.blue()):
        return discord.Embed(description=description, color=color)

    # --- Basic Mod ---
    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(embed=self.create_embed(f"🔒 {channel.mention} has been locked.", discord.Color.orange()))

    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(embed=self.create_embed(f"🔓 {channel.mention} has been unlocked.", discord.Color.green()))

    @app_commands.command(name="purge", description="Purge messages in a channel")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer()
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(embed=self.create_embed(f"🗑️ Purged {len(deleted)} messages."), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    # --- Advanced Mod (MEE6 like) ---
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(embed=self.create_embed(f"👢 {member.mention} has been kicked. Reason: `{reason}`", discord.Color.red()))
        except Exception as e:
            await interaction.response.send_message(f"Could not kick member. Make sure my role is higher than theirs. Error: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(embed=self.create_embed(f"🔨 {member.mention} has been banned. Reason: `{reason}`", discord.Color.dark_red()))
        except Exception as e:
            await interaction.response.send_message(f"Could not ban member. Error: {e}", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        try:
            duration = timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            await interaction.response.send_message(embed=self.create_embed(f"⏱️ {member.mention} has been timed out for {minutes}m. Reason: `{reason}`", discord.Color.orange()))
        except Exception as e:
            await interaction.response.send_message(f"Could not timeout member. Error: {e}", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.timeout(None)
            await interaction.response.send_message(embed=self.create_embed(f"✅ Removed timeout from {member.mention}.", discord.Color.green()))
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    # --- Warnings ---
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        self.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        embed = self.create_embed(f"⚠️ {member.mention} has been warned. Reason: `{reason}`", discord.Color.yellow())
        await interaction.response.send_message(embed=embed)
        try:
            await member.send(f"You have been warned in **{interaction.guild.name}** for: `{reason}`")
        except:
            pass

    @app_commands.command(name="warnings", description="Check warnings for a member")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings_list(self, interaction: discord.Interaction, member: discord.Member):
        warns = self.get_warnings(interaction.guild_id, member.id)
        if not warns:
            await interaction.response.send_message(embed=self.create_embed(f"✅ {member.mention} has no warnings.", discord.Color.green()))
            return
            
        desc = ""
        for i, w in enumerate(warns):
            desc += f"**{i+1}.** <@{w['moderator']}> - `{w['reason']}`\n"
            
        embed = discord.Embed(title=f"Warnings for {member.display_name}", description=desc, color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear_warnings", description="Clear warnings for a member")
    @app_commands.default_permissions(moderate_members=True)
    async def clear_warnings(self, interaction: discord.Interaction, member: discord.Member):
        self.clear_user_warnings(interaction.guild_id, member.id)
        await interaction.response.send_message(embed=self.create_embed(f"🧹 Cleared all warnings for {member.mention}.", discord.Color.green()))

    # --- Role Management ---
    role_group = app_commands.Group(name="role", description="Role management commands")

    @role_group.command(name="add", description="Add a role to a user")
    @app_commands.default_permissions(manage_roles=True)
    async def role_add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role)
            await interaction.response.send_message(embed=self.create_embed(f"✅ Added {role.mention} to {member.mention}.", discord.Color.green()))
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from a user")
    @app_commands.default_permissions(manage_roles=True)
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role)
            await interaction.response.send_message(embed=self.create_embed(f"❌ Removed {role.mention} from {member.mention}.", discord.Color.red()))
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    # --- Automod ---
    automod_group = app_commands.Group(name="automod", description="Automod configuration")

    @automod_group.command(name="add_banned_word", description="Add a banned word")
    @app_commands.default_permissions(administrator=True)
    async def add_banned_word(self, interaction: discord.Interaction, word: str):
        self.add_banned_word(interaction.guild_id, word)
        await interaction.response.send_message(embed=self.create_embed(f"✅ Added `{word}` to banned words filter.", discord.Color.green()))

    @automod_group.command(name="remove_banned_word", description="Remove a banned word")
    @app_commands.default_permissions(administrator=True)
    async def remove_banned_word(self, interaction: discord.Interaction, word: str):
        self.remove_banned_word(interaction.guild_id, word)
        await interaction.response.send_message(embed=self.create_embed(f"✅ Removed `{word}` from banned words filter.", discord.Color.green()))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
            
        content = message.content.lower()
        banned_words = self.get_banned_words(message.guild.id)
        for word in banned_words:
            if word in content:
                try:
                    await message.delete()
                    await message.author.send(f"Your message in **{message.guild.name}** was deleted for containing a banned word: `{word}`")
                except:
                    pass
                break

async def setup(bot):
    await bot.add_cog(Moderation(bot))
