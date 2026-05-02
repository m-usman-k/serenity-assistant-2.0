import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class ReactionRoleView(discord.ui.View):
    def __init__(self, role: discord.Role):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Get/Remove Role", style=discord.ButtonStyle.primary, custom_id="reaction_role_button")
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.role in interaction.user.roles:
            await interaction.user.remove_roles(self.role)
            await interaction.response.send_message(embed=discord.Embed(description=f"Removed role {self.role.name}", color=discord.Color.red()), ephemeral=True)
        else:
            await interaction.user.add_roles(self.role)
            await interaction.response.send_message(embed=discord.Embed(description=f"Added role {self.role.name}", color=discord.Color.green()), ephemeral=True)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "database.sqlite"
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stickies 
                     (channel_id TEXT PRIMARY KEY, message_id TEXT, content TEXT)''')
        conn.commit()
        conn.close()

    def get_sticky(self, channel_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT message_id, content FROM stickies WHERE channel_id=?", (str(channel_id),))
        result = c.fetchone()
        conn.close()
        return {"message_id": result[0], "content": result[1]} if result else None

    def set_sticky(self, channel_id, message_id, content):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO stickies (channel_id, message_id, content) VALUES (?, ?, ?)", 
                  (str(channel_id), str(message_id), str(content)))
        conn.commit()
        conn.close()

    def remove_sticky(self, channel_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("DELETE FROM stickies WHERE channel_id=?", (str(channel_id),))
        conn.commit()
        conn.close()

    def create_embed(self, description):
        return discord.Embed(description=description, color=discord.Color.blue())

    @app_commands.command(name="sticky_add", description="Set a sticky message for this channel")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_add(self, interaction: discord.Interaction, message: str):
        embed = discord.Embed(title="📌 Sticky Note", description=message, color=discord.Color.gold())
        msg = await interaction.channel.send(embed=embed)
        self.set_sticky(interaction.channel_id, msg.id, message)
        await interaction.response.send_message(embed=self.create_embed("Sticky note added."), ephemeral=True)

    @app_commands.command(name="sticky_remove", description="Remove the sticky message from this channel")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_remove(self, interaction: discord.Interaction):
        sticky = self.get_sticky(interaction.channel_id)
        if sticky:
            self.remove_sticky(interaction.channel_id)
            await interaction.response.send_message(embed=self.create_embed("Sticky note removed."), ephemeral=True)
        else:
            await interaction.response.send_message(embed=self.create_embed("No sticky note in this channel."), ephemeral=True)

    @app_commands.command(name="reaction_role", description="Set up a button reaction role")
    @app_commands.default_permissions(manage_roles=True)
    async def reaction_role(self, interaction: discord.Interaction, role: discord.Role, message: str):
        embed = self.create_embed(message)
        view = ReactionRoleView(role)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
            
        sticky = self.get_sticky(message.channel.id)
        if sticky:
            try:
                old_msg = await message.channel.fetch_message(int(sticky["message_id"]))
                await old_msg.delete()
            except:
                pass
            
            embed = discord.Embed(title="📌 Sticky Note", description=sticky["content"], color=discord.Color.gold())
            new_msg = await message.channel.send(embed=embed)
            self.set_sticky(message.channel.id, new_msg.id, sticky["content"])

async def setup(bot):
    await bot.add_cog(Utility(bot))
