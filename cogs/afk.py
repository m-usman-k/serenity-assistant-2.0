import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector

class AFK(commands.Cog):
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
        c.execute('''CREATE TABLE IF NOT EXISTS serenity_afk 
                     (guild_id VARCHAR(255), user_id VARCHAR(255), reason TEXT, 
                     PRIMARY KEY (guild_id, user_id))''')
        conn.commit()
        conn.close()

    def set_afk(self, guild_id, user_id, reason):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("REPLACE INTO serenity_afk (guild_id, user_id, reason) VALUES (%s, %s, %s)", 
                  (str(guild_id), str(user_id), reason))
        conn.commit()
        conn.close()

    def get_afk(self, guild_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT reason FROM serenity_afk WHERE guild_id=%s AND user_id=%s", (str(guild_id), str(user_id)))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def remove_afk(self, guild_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_afk WHERE guild_id=%s AND user_id=%s", (str(guild_id), str(user_id)))
        conn.commit()
        conn.close()

    def create_embed(self, description):
        return discord.Embed(description=description, color=discord.Color.blue())

    @app_commands.command(name="afk_set", description="Set your AFK status")
    async def afk_set(self, interaction: discord.Interaction, reason: str = "AFK"):
        self.set_afk(interaction.guild_id, interaction.user.id, reason)
        await interaction.response.send_message(embed=self.create_embed(f"You are now AFK: **{reason}**"))

    @app_commands.command(name="afk_clear", description="Clear your AFK status")
    async def afk_clear(self, interaction: discord.Interaction):
        if self.get_afk(interaction.guild_id, interaction.user.id):
            self.remove_afk(interaction.guild_id, interaction.user.id)
            await interaction.response.send_message(embed=self.create_embed("👋 Welcome back! Your AFK status has been cleared."))
        else:
            await interaction.response.send_message(embed=self.create_embed("You are not currently AFK."), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Auto clear AFK
        if self.get_afk(message.guild.id, message.author.id):
            self.remove_afk(message.guild.id, message.author.id)
            try:
                await message.channel.send(embed=self.create_embed(f"👋 Welcome back {message.author.mention}! Your AFK status has been cleared."), delete_after=5)
            except discord.Forbidden:
                pass

        # Check for mentions of AFK users
        for mention in message.mentions:
            if mention.id == message.author.id: # Don't trigger for yourself
                continue
            reason = self.get_afk(message.guild.id, mention.id)
            if reason:
                try:
                    await message.channel.send(embed=self.create_embed(f"{mention.display_name} is currently AFK: **{reason}**"), delete_after=5)
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(AFK(bot))
