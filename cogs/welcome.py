import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
from easy_pil import Editor, load_image_async, Font

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "database.sqlite"
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS config 
                     (guild_id TEXT, key TEXT, value TEXT, 
                     PRIMARY KEY (guild_id, key))''')
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

    async def generate_card(self, member: discord.Member, title_text: str, subtitle_text: str, color: str):
        # Create a base image
        background = Editor("https://img.freepik.com/free-vector/abstract-dark-blue-polygonal-background_1035-17545.jpg").resize((800, 250))
        
        try:
            profile_image = await load_image_async(str(member.display_avatar.url))
            profile = Editor(profile_image).resize((150, 150)).circle_image()
            background.paste(profile, (50, 50))
        except:
            pass

        poppins = Font.poppins(size=40, variant="bold")
        poppins_small = Font.poppins(size=30, variant="regular")

        background.text((250, 90), title_text, color="white", font=poppins)
        background.text((250, 140), subtitle_text, color=color, font=poppins_small)

        file = discord.File(fp=background.image_bytes, filename="card.png")
        return file

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel_id = self.get_config(member.guild.id, "welcome_channel")
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                try:
                    file = await self.generate_card(
                        member, 
                        f"WELCOME, {member.name.upper()}!", 
                        f"You are the {member.guild.member_count}th member", 
                        "#00ff00"
                    )
                    
                    msg_template = self.get_config(member.guild.id, "welcome_message") or "Welcome {user.mention} to {server}!"
                    msg = msg_template.replace("{user.mention}", member.mention).replace("{user.name}", member.name).replace("{server}", member.guild.name)
                    
                    await channel.send(content=msg, file=file)
                except Exception as e:
                    print(f"Error sending welcome card: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel_id = self.get_config(member.guild.id, "goodbye_channel")
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                try:
                    file = await self.generate_card(
                        member, 
                        f"GOODBYE, {member.name.upper()}!", 
                        f"We will miss you!", 
                        "#ff0000"
                    )
                    await channel.send(file=file)
                except Exception as e:
                    print(f"Error sending goodbye card: {e}")

    welcome_group = app_commands.Group(name="welcome_setup", description="Setup welcome and goodbye messages")

    @welcome_group.command(name="set_channel", description="Set the channel for welcome messages")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.set_config(interaction.guild_id, "welcome_channel", channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ Welcome channel set to {channel.mention}", color=discord.Color.green()))

    @welcome_group.command(name="set_message", description="Set the welcome message text")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_message(self, interaction: discord.Interaction, message: str):
        self.set_config(interaction.guild_id, "welcome_message", message)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ Welcome message updated to:\n`{message}`", color=discord.Color.green()))

    @welcome_group.command(name="set_goodbye_channel", description="Set the channel for goodbye messages")
    @app_commands.default_permissions(administrator=True)
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.set_config(interaction.guild_id, "goodbye_channel", channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ Goodbye channel set to {channel.mention}", color=discord.Color.green()))

async def setup(bot):
    await bot.add_cog(Welcome(bot))
