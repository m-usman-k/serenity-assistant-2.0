import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
from datetime import datetime, timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_db()

    def get_connection(self):
        return mysql.connector.connect(
            host="13.212.150.216",
            port=3306,
            user="simpleprog",
            password="jf83hj032fjkldsa",
            database="simpleprog_db"
        )

    def setup_db(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS serenity_warnings 
                     (id BIGINT PRIMARY KEY AUTO_INCREMENT, 
                     guild_id VARCHAR(255), user_id VARCHAR(255), moderator VARCHAR(255), reason TEXT, timestamp TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS serenity_banned_words 
                     (guild_id VARCHAR(255), word VARCHAR(255), PRIMARY KEY (guild_id, word))''')
        conn.commit()
        conn.close()

    def add_warning(self, guild_id, user_id, moderator, reason):
        conn = self.get_connection()
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO serenity_warnings (guild_id, user_id, moderator, reason, timestamp) VALUES (%s, %s, %s, %s, %s)", 
                  (str(guild_id), str(user_id), str(moderator), reason, timestamp))
        conn.commit()
        conn.close()

    def get_warnings(self, guild_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT moderator, reason, timestamp FROM serenity_warnings WHERE guild_id=%s AND user_id=%s", (str(guild_id), str(user_id)))
        rows = c.fetchall()
        conn.close()
        return [{"moderator": r[0], "reason": r[1], "timestamp": r[2]} for r in rows]

    def clear_user_warnings(self, guild_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_warnings WHERE guild_id=%s AND user_id=%s", (str(guild_id), str(user_id)))
        conn.commit()
        conn.close()

    def add_banned_word(self, guild_id, word):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("INSERT IGNORE INTO serenity_banned_words (guild_id, word) VALUES (%s, %s)", (str(guild_id), word.lower()))
        conn.commit()
        conn.close()

    def remove_banned_word(self, guild_id, word):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_banned_words WHERE guild_id=%s AND word=%s", (str(guild_id), word.lower()))
        conn.commit()
        conn.close()

    def get_banned_words(self, guild_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT word FROM serenity_banned_words WHERE guild_id=%s", (str(guild_id),))
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def create_embed(self, description, color):
        return discord.Embed(description=description, color=color, timestamp=datetime.now())

    # --- Basic Mod ---
    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(embed=self.create_embed(f"Channel {channel.mention} has been locked.", discord.Color.orange()))

    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(embed=self.create_embed(f"Channel {channel.mention} has been unlocked.", discord.Color.green()))

    @app_commands.command(name="purge", description="Purge messages in a channel")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(embed=self.create_embed(f"Purged {len(deleted)} messages."), ephemeral=True)
        except Exception as e:
            try:
                await interaction.followup.send(f"Error: {e}", ephemeral=True)
            except:
                pass

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(embed=self.create_embed(f"{member.mention} has been kicked. Reason: `{reason}`", discord.Color.red()))
        except Exception as e:
            await interaction.response.send_message(f"Could not kick member. Make sure my role is higher than theirs. Error: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(embed=self.create_embed(f"{member.mention} has been banned. Reason: `{reason}`", discord.Color.dark_red()))
        except Exception as e:
            await interaction.response.send_message(f"Could not ban member. Error: {e}", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        try:
            duration = timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            await interaction.response.send_message(embed=self.create_embed(f"{member.mention} has been timed out for `{minutes}m`. Reason: `{reason}`", discord.Color.orange()))
        except Exception as e:
            await interaction.response.send_message(f"Could not timeout member. Error: {e}", ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        self.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        embed = self.create_embed(f"{member.mention} has been warned. Reason: `{reason}`", discord.Color.yellow())
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
            await interaction.response.send_message(embed=self.create_embed(f"{member.mention} has no warnings.", discord.Color.green()))
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
        await interaction.response.send_message(embed=self.create_embed(f"Cleared all warnings for {member.mention}.", discord.Color.green()))

    # --- Role Management ---
    role_group = app_commands.Group(name="role", description="Role management commands")

    @role_group.command(name="add", description="Add a role to a user")
    @app_commands.default_permissions(manage_roles=True)
    async def role_add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if interaction.guild.me.top_role <= role:
            await interaction.response.send_message("I cannot add this role because it is higher than or equal to my own role in the server hierarchy.", ephemeral=True)
            return
        try:
            await member.add_roles(role)
            await interaction.response.send_message(embed=self.create_embed(f"Added role `{role.name}` to {member.mention}.", discord.Color.green()))
        except discord.Forbidden:
            await interaction.response.send_message("I don't have the `Manage Roles` permission or my role is too low in the hierarchy.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from a user")
    @app_commands.default_permissions(manage_roles=True)
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if interaction.guild.me.top_role <= role:
            await interaction.response.send_message("I cannot remove this role because it is higher than or equal to my own role in the server hierarchy.", ephemeral=True)
            return
        try:
            await member.remove_roles(role)
            await interaction.response.send_message(embed=self.create_embed(f"Removed role `{role.name}` from {member.mention}.", discord.Color.red()))
        except discord.Forbidden:
            await interaction.response.send_message("I don't have the `Manage Roles` permission or my role is too low in the hierarchy.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    # --- Automod ---
    automod_group = app_commands.Group(name="automod", description="Automod configuration")

    @automod_group.command(name="add_banned_word", description="Add a banned word")
    @app_commands.default_permissions(administrator=True)
    async def add_banned_word_cmd(self, interaction: discord.Interaction, word: str):
        self.add_banned_word(interaction.guild_id, word)
        await interaction.response.send_message(embed=self.create_embed(f"Added `{word}` to banned words filter.", discord.Color.green()))

    @automod_group.command(name="remove_banned_word", description="Remove a banned word")
    @app_commands.default_permissions(administrator=True)
    async def remove_banned_word_cmd(self, interaction: discord.Interaction, word: str):
        self.remove_banned_word(interaction.guild_id, word)
        await interaction.response.send_message(embed=self.create_embed(f"Removed `{word}` from banned words filter.", discord.Color.green()))

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
                    await message.channel.send(f"{message.author.mention}, your message was removed because it contained a banned word.", delete_after=5)
                except:
                    pass
                break

async def setup(bot):
    await bot.add_cog(Moderation(bot))
