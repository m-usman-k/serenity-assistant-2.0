import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "database.sqlite"
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS economy 
                     (user_id TEXT, guild_id TEXT, balance INTEGER, 
                     PRIMARY KEY (user_id, guild_id))''')
        conn.commit()
        conn.close()

    def get_balance(self, user_id, guild_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT balance FROM economy WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id)))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0

    def set_balance(self, user_id, guild_id, amount):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO economy (user_id, guild_id, balance) VALUES (?, ?, ?)", 
                  (str(user_id), str(guild_id), amount))
        conn.commit()
        conn.close()

    def add_balance(self, user_id, guild_id, amount):
        bal = self.get_balance(user_id, guild_id)
        self.set_balance(user_id, guild_id, bal + amount)

    def remove_balance(self, user_id, guild_id, amount):
        bal = self.get_balance(user_id, guild_id)
        self.set_balance(user_id, guild_id, max(0, bal - amount))

    @app_commands.command(name="balance", description="Check your or someone else's wallet balance")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        bal = self.get_balance(member.id, interaction.guild_id)
        
        embed = discord.Embed(title=f"💰 {member.display_name}'s Balance", description=f"**Wallet:** `{bal}` coins", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Work to earn some coins")
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild_id, i.user.id)) # 1 hour cooldown
    async def work(self, interaction: discord.Interaction):
        import random
        earned = random.randint(50, 200)
        self.add_balance(interaction.user.id, interaction.guild_id, earned)
        
        await interaction.response.send_message(embed=discord.Embed(description=f"💼 You worked hard and earned `{earned}` coins!", color=discord.Color.green()))

    @work.error
    async def work_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"You are tired! Try again in `{error.retry_after:.2f}` seconds.", ephemeral=True)

    @app_commands.command(name="pay", description="Pay coins to another user")
    async def pay(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
            
        bal = self.get_balance(interaction.user.id, interaction.guild_id)
        if bal < amount:
            await interaction.response.send_message("You don't have enough coins!", ephemeral=True)
            return
            
        self.remove_balance(interaction.user.id, interaction.guild_id, amount)
        self.add_balance(member.id, interaction.guild_id, amount)
        
        await interaction.response.send_message(embed=discord.Embed(description=f"💸 You paid {member.mention} `{amount}` coins.", color=discord.Color.green()))

    eco_group = app_commands.Group(name="economy_admin", description="Economy Admin Commands")

    @eco_group.command(name="add_money", description="Add money to a user's balance")
    @app_commands.default_permissions(administrator=True)
    async def add_money(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        self.add_balance(member.id, interaction.guild_id, amount)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ Added `{amount}` coins to {member.mention}'s balance.", color=discord.Color.green()))

    @eco_group.command(name="remove_money", description="Remove money from a user's balance")
    @app_commands.default_permissions(administrator=True)
    async def remove_money(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        self.remove_balance(member.id, interaction.guild_id, amount)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ Removed `{amount}` coins from {member.mention}'s balance.", color=discord.Color.green()))

async def setup(bot):
    await bot.add_cog(Economy(bot))
