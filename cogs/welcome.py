import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
from datetime import datetime, timezone



# ──────────────────────────────────────────────
# Supported variables (shown in modal placeholder)
# ──────────────────────────────────────────────
VARIABLE_REFERENCE = (
    "{user}          → Username\n"
    "{user.mention}  → @Mention the user\n"
    "{user.name}     → Username\n"
    "{user.id}       → User's Discord ID\n"
    "{user.tag}      → Full tag (username#0000)\n"
    "{server}        → Server name\n"
    "{server.count}  → Total member count\n"
    "{server.id}     → Server's Discord ID\n"
    "{channel}       → Mention the welcome channel"
)

DEFAULT_WELCOME = "Hey {user.mention}, welcome to **{server}**! You are member **#{server.count}**."
DEFAULT_GOODBYE = "**{user.name}** has left the server. We now have **{server.count}** members."


def resolve(template: str, member: discord.Member, channel: discord.TextChannel = None) -> str:
    return (
        template
        .replace("{user}", member.name)
        .replace("{user.mention}", member.mention)
        .replace("{user.name}", member.name)
        .replace("{user.id}", str(member.id))
        .replace("{user.tag}", str(member))
        .replace("{server}", member.guild.name)
        .replace("{server.count}", str(member.guild.member_count))
        .replace("{server.id}", str(member.guild.id))
        .replace("{channel}", channel.mention if channel else "")
    )


# ──────────────────────────────────────────────
# Modals
# ──────────────────────────────────────────────
class WelcomeMessageModal(discord.ui.Modal, title="Configure Welcome Message"):
    message_input = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.long,
        placeholder="e.g. Hey {user.mention}, welcome to **{server}**! You are member #{server.count}.",
        required=True,
        max_length=2000
    )

    def __init__(self, cog, current: str = ""):
        super().__init__()
        self.cog = cog
        if current:
            self.message_input.default = current

    async def on_submit(self, interaction: discord.Interaction):
        self.cog.set_config(interaction.guild_id, "welcome_message", self.message_input.value)
        preview = resolve(self.message_input.value, interaction.user)
        embed = discord.Embed(
            title="Welcome Message Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Preview", value=preview[:1024], inline=False)
        embed.set_footer(text="This is a preview using your account. Real message will use the joining member's data.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


class GoodbyeMessageModal(discord.ui.Modal, title="Configure Goodbye Message"):
    message_input = discord.ui.TextInput(
        label="Goodbye Message",
        style=discord.TextStyle.long,
        placeholder="e.g. {user.name} has left **{server}**. We now have {server.count} members.",
        required=True,
        max_length=2000
    )

    def __init__(self, cog, current: str = ""):
        super().__init__()
        self.cog = cog
        if current:
            self.message_input.default = current

    async def on_submit(self, interaction: discord.Interaction):
        self.cog.set_config(interaction.guild_id, "goodbye_message", self.message_input.value)
        preview = resolve(self.message_input.value, interaction.user)
        embed = discord.Embed(
            title="Goodbye Message Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Preview", value=preview[:1024], inline=False)
        embed.set_footer(text="This is a preview using your account. Real message will use the leaving member's data.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────
class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_config(self, guild_id, key):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT config_value FROM serenity_config WHERE guild_id=%s AND config_key=%s", (str(guild_id), key))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_config(self, guild_id, key, value):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("REPLACE INTO serenity_config (guild_id, config_key, config_value) VALUES (%s, %s, %s)",
                  (str(guild_id), key, str(value)))
        conn.commit()
        conn.close()

    # ──────────────────────────────────────────────
    # Card generation
    # ──────────────────────────────────────────────
    async def generate_card(self, member: discord.Member, title_text: str, subtitle_text: str, accent_color: tuple, bg_path: str = None):
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
        from easy_pil import Editor, Font
        import io
        import aiohttp
        import os

        W, H = 900, 280

        # Try to load custom background if provided
        bg_img = None
        if bg_path and os.path.exists(bg_path):
            try:
                bg_img = Image.open(bg_path).convert("RGBA").resize((W, H))
            except:
                pass
        
        if not bg_img:
            # Fallback: Simple dark gradient background
            bg_img = Image.new("RGBA", (W, H), (15, 15, 35, 255))
            draw = ImageDraw.Draw(bg_img)
            for x in range(W):
                r = int(15 + 20 * x / W)
                g = int(15 + 15 * x / W)
                b = int(35 + 40 * x / W)
                draw.line([(x, 0), (x, H)], fill=(r, g, b, 255))
        else:
            # Apply a darkening overlay for better text readability on custom images
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
            bg_img = Image.alpha_composite(bg_img, overlay)

        # Accent bar at bottom
        draw = ImageDraw.Draw(bg_img)
        draw.rectangle([0, H - 6, W, H], fill=(*accent_color, 255))

        background = Editor(bg_img.convert("RGB"))

        # Circular avatar on the left
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(member.display_avatar.url)) as resp:
                    avatar_bytes = await resp.read()
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((150, 150))
            avatar_editor = Editor(avatar_img).circle_image()
            background.paste(avatar_editor, (50, 65))
        except Exception as e:
            print(f"Avatar load error: {e}")

        poppins_bold  = Font.poppins(size=38, variant="bold")
        poppins_small = Font.poppins(size=26, variant="regular")

        hex_accent = "#{:02x}{:02x}{:02x}".format(*accent_color)
        background.text((230, 95),  title_text,    color="white",     font=poppins_bold)
        background.text((230, 150), subtitle_text, color=hex_accent,  font=poppins_small)

        return discord.File(fp=background.image_bytes, filename="card.png")

    # ──────────────────────────────────────────────
    # Listeners
    # ──────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel_id = self.get_config(member.guild.id, "welcome_channel")
        if not channel_id:
            return
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        try:
            msg_template = self.get_config(member.guild.id, "welcome_message") or DEFAULT_WELCOME
            msg = resolve(msg_template, member, channel)

            bg_path = self.get_config(member.guild.id, "welcome_bg_path")
            file = await self.generate_card(
                member,
                f"WELCOME, {member.name.upper()}!",
                f"Member #{member.guild.member_count}",
                (0, 220, 120),
                bg_path=bg_path
            )
            await channel.send(content=msg, file=file)

        except Exception as e:
            print(f"Error sending welcome card: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel_id = self.get_config(member.guild.id, "goodbye_channel")
        if not channel_id:
            return
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        try:
            msg_template = self.get_config(member.guild.id, "goodbye_message") or DEFAULT_GOODBYE
            msg = resolve(msg_template, member, channel)

            bg_path = self.get_config(member.guild.id, "goodbye_bg_path")
            file = await self.generate_card(
                member,
                f"GOODBYE, {member.name.upper()}!",
                f"We will miss you.",
                (220, 60, 60),
                bg_path=bg_path
            )
            await channel.send(content=msg, file=file)

        except Exception as e:
            print(f"Error sending goodbye card: {e}")

    # ──────────────────────────────────────────────
    # Commands
    # ──────────────────────────────────────────────
    welcome_group = app_commands.Group(name="welcome", description="Welcome and goodbye settings")

    @welcome_group.command(name="set_channel", description="Set the channel for welcome messages")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.set_config(interaction.guild_id, "welcome_channel", channel.id)
        embed = discord.Embed(
            title="Welcome Channel Set",
            description=f"Welcome messages will be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Use /welcome set_message to customise the message text.")
        await interaction.response.send_message(embed=embed)

    @welcome_group.command(name="set_goodbye_channel", description="Set the channel for goodbye messages")
    @app_commands.default_permissions(administrator=True)
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.set_config(interaction.guild_id, "goodbye_channel", channel.id)
        embed = discord.Embed(
            title="Goodbye Channel Set",
            description=f"Goodbye messages will be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Use /welcome set_goodbye_message to customise the message text.")
        await interaction.response.send_message(embed=embed)

    @welcome_group.command(name="set_message", description="Open a modal to write the welcome message")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_message(self, interaction: discord.Interaction):
        current = self.get_config(interaction.guild_id, "welcome_message") or ""
        await interaction.response.send_modal(WelcomeMessageModal(self, current))

    @welcome_group.command(name="set_goodbye_message", description="Open a modal to write the goodbye message")
    @app_commands.default_permissions(administrator=True)
    async def set_goodbye_message(self, interaction: discord.Interaction):
        current = self.get_config(interaction.guild_id, "goodbye_message") or ""
        await interaction.response.send_modal(GoodbyeMessageModal(self, current))

    @welcome_group.command(name="variables", description="Show all supported message variables")
    @app_commands.default_permissions(administrator=True)
    async def variables(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Supported Welcome / Goodbye Variables",
            description=f"```{VARIABLE_REFERENCE}```",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Use these in /welcome set_message and /welcome set_goodbye_message")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="preview", description="Preview the current welcome or goodbye card and message")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
    ])
    async def preview(self, interaction: discord.Interaction, type: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        channel_id = self.get_config(interaction.guild_id, f"{'welcome' if type.value == 'welcome' else 'goodbye'}_channel")
        channel = self.bot.get_channel(int(channel_id)) if channel_id else interaction.channel

        if type.value == "welcome":
            msg_template = self.get_config(interaction.guild_id, "welcome_message") or DEFAULT_WELCOME
            msg = resolve(msg_template, member, channel)
            accent = (0, 220, 120)
            card_title = f"WELCOME, {member.name.upper()}!"
            card_sub = f"Member #{interaction.guild.member_count}"
        else:
            msg_template = self.get_config(interaction.guild_id, "goodbye_message") or DEFAULT_GOODBYE
            msg = resolve(msg_template, member, channel)
            accent = (220, 60, 60)
            card_title = f"GOODBYE, {member.name.upper()}!"
            card_sub = f"We will miss you."

        try:
            bg_key = "welcome_bg_path" if type.value == "welcome" else "goodbye_bg_path"
            bg_path = self.get_config(interaction.guild_id, bg_key)
            
            file = await self.generate_card(member, card_title, card_sub, accent, bg_path=bg_path)
            embed = discord.Embed(
                title=f"Preview — {type.name} Message",
                description=f"**Message text:**\n{msg}",
                color=discord.Color.from_rgb(*accent)
            )
            embed.set_image(url="attachment://card.png")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating preview: `{e}`", ephemeral=True)

    @welcome_group.command(name="disable", description="Disable welcome or goodbye messages")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Welcome", value="welcome_channel"),
        app_commands.Choice(name="Goodbye", value="goodbye_channel"),
    ])
    async def disable(self, interaction: discord.Interaction, type: app_commands.Choice[str]):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_config WHERE guild_id=%s AND config_key=%s", (str(interaction.guild_id), type.value))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"{type.name} messages disabled.", color=discord.Color.green()),
            ephemeral=True
        )

    @welcome_group.command(name="set_background", description="Upload a custom background for welcome cards")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_background(self, interaction: discord.Interaction, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message("❌ Please upload a valid image file.", ephemeral=True)
            return

        import os
        assets_dir = "assets"
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
        
        path = os.path.join(assets_dir, f"welcome_bg_{interaction.guild_id}.png")
        await image.save(path)
        
        self.set_config(interaction.guild_id, "welcome_bg_path", path)
        await interaction.response.send_message(f"Welcome background updated!", ephemeral=True)

    @welcome_group.command(name="set_goodbye_background", description="Upload a custom background for goodbye cards")
    @app_commands.default_permissions(administrator=True)
    async def set_goodbye_background(self, interaction: discord.Interaction, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message("❌ Please upload a valid image file.", ephemeral=True)
            return

        import os
        assets_dir = "assets"
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
        
        path = os.path.join(assets_dir, f"goodbye_bg_{interaction.guild_id}.png")
        await image.save(path)
        
        self.set_config(interaction.guild_id, "goodbye_bg_path", path)
        await interaction.response.send_message(f"Goodbye background updated!", ephemeral=True)

    @welcome_group.command(name="reset_background", description="Reset background to default gradient")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Welcome", value="welcome_bg_path"),
        app_commands.Choice(name="Goodbye", value="goodbye_bg_path"),
    ])
    async def reset_background(self, interaction: discord.Interaction, type: app_commands.Choice[str]):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_config WHERE guild_id=%s AND config_key=%s", (str(interaction.guild_id), type.value))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"{type.name} background reset to default.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
