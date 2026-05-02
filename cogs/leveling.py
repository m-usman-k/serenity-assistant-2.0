import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "database.sqlite"
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS leveling 
                     (user_id TEXT, guild_id TEXT, xp INTEGER, level INTEGER, 
                     PRIMARY KEY (user_id, guild_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS config 
                     (guild_id TEXT, key TEXT, value TEXT, 
                     PRIMARY KEY (guild_id, key))''')
        conn.commit()
        conn.close()

    def get_xp_for_level(self, level):
        return 5 * (level ** 2) + (50 * level) + 100

    def get_user(self, user_id, guild_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT xp, level FROM leveling WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id)))
        result = c.fetchone()
        conn.close()
        if result:
            return {"xp": result[0], "level": result[1]}
        return {"xp": 0, "level": 0}

    def update_user(self, user_id, guild_id, xp, level):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO leveling (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)", 
                  (str(user_id), str(guild_id), xp, level))
        conn.commit()
        conn.close()

    def get_config(self, guild_id, key):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT value FROM config WHERE guild_id=? AND key=?", (str(guild_id), key))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_config(self, guild_id, key, value):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (guild_id, key, value) VALUES (?, ?, ?)", (str(guild_id), key, str(value)))
        conn.commit()
        conn.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_data = self.get_user(message.author.id, message.guild.id)
        
        # Add random XP between 15 and 25
        new_xp = user_data["xp"] + random.randint(15, 25)
        current_level = user_data["level"]
        xp_needed = self.get_xp_for_level(current_level)

        if new_xp >= xp_needed:
            current_level += 1
            new_xp -= xp_needed
            self.update_user(message.author.id, message.guild.id, new_xp, current_level)

            channel_id = self.get_config(message.guild.id, "level_channel")
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(f"GG {message.author.mention}, you just advanced to level **{current_level}**!")
            else:
                await message.channel.send(f"GG {message.author.mention}, you just advanced to level **{current_level}**!")
        else:
            self.update_user(message.author.id, message.guild.id, new_xp, current_level)

    @app_commands.command(name="rank", description="Check your or someone else's current level and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        data = self.get_user(member.id, interaction.guild_id)
        
        xp_needed = self.get_xp_for_level(data['level'])
        
        embed = discord.Embed(title=f"{member.display_name}'s Rank", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"`{data['level']}`", inline=True)
        embed.add_field(name="XP", value=f"`{data['xp']} / {xp_needed}`", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the top members with the most XP")
    async def leaderboard(self, interaction: discord.Interaction):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT user_id, xp, level FROM leveling WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10", (str(interaction.guild_id),))
        results = c.fetchall()
        conn.close()
        
        embed = discord.Embed(title="🏆 XP Leaderboard", color=discord.Color.gold())
        
        desc = ""
        for index, (user_id, xp, level) in enumerate(results):
            user = interaction.guild.get_member(int(user_id))
            name = user.display_name if user else f"Unknown User ({user_id})"
            desc += f"**{index + 1}.** {name} - Level `{level}` | `{xp}` XP\n"
            
        embed.description = desc or "No one is on the leaderboard yet!"
        await interaction.response.send_message(embed=embed)

    level_group = app_commands.Group(name="leveling_setup", description="Setup leveling system")

    @level_group.command(name="set_channel", description="Set the channel for level up messages")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.set_config(interaction.guild_id, "level_channel", channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ Level up channel set to {channel.mention}", color=discord.Color.green()))

async def setup(bot):
    await bot.add_cog(Leveling(bot))
