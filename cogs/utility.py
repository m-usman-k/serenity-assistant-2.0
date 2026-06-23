import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector



# ──────────────────────────────────────────────
# Modals
# ──────────────────────────────────────────────
class StickyCreateModal(discord.ui.Modal, title="Configure Sticky Message"):
    sticky_title = discord.ui.TextInput(
        label="Title (optional)",
        required=False,
        max_length=256,
        placeholder="e.g. Server Rules"
    )
    content = discord.ui.TextInput(
        label="Message Content",
        style=discord.TextStyle.long,
        required=True,
        max_length=2000,
        placeholder="Write your sticky message here..."
    )

    def __init__(self, cog, channel: discord.TextChannel, is_embed: bool):
        super().__init__()
        self.cog = cog
        self.channel = channel
        self.is_embed = is_embed
        
        # Pre-fill if editing
        current = self.cog.get_sticky(channel.id)
        if current:
            self.sticky_title.default = current.get("title") or ""
            self.content.default = current.get("content") or ""

    async def on_submit(self, interaction: discord.Interaction):
        title_val   = self.sticky_title.value.strip() or None
        content_val = self.content.value.strip()

        self.cog.create_or_update_sticky(interaction.guild_id, self.channel.id, title_val, content_val, is_embed=self.is_embed)
        await self.cog.post_sticky(self.channel)

        await interaction.response.send_message(f"Sticky message updated in `{self.channel.name}`.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Error: `{error}`", ephemeral=True)


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_counter: dict[int, int] = {}
        self._last_post = {}

    # ── DB helpers ──────────────────────────────
    def create_or_update_sticky(self, guild_id, channel_id, title, content, is_embed=True):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO serenity_stickies (guild_id, channel_id, title, content, is_embed) VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE title=VALUES(title), content=VALUES(content), is_embed=VALUES(is_embed)",
            (str(guild_id), str(channel_id), title, content, int(is_embed))
        )
        conn.commit()
        conn.close()

    def get_sticky(self, channel_id) -> dict | None:
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT channel_id, guild_id, title, content, message_id, enabled, cooldown, is_embed FROM serenity_stickies WHERE channel_id=%s",
                  (str(channel_id),))
        row = c.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def get_guild_stickies(self, guild_id) -> list[dict]:
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT channel_id, guild_id, title, content, message_id, enabled, cooldown, is_embed FROM serenity_stickies WHERE guild_id=%s",
                  (str(guild_id),))
        rows = c.fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def set_sticky_enabled(self, channel_id, enabled: bool):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE serenity_stickies SET enabled=%s WHERE channel_id=%s", (int(enabled), str(channel_id)))
        conn.commit()
        conn.close()

    def set_sticky_cooldown(self, channel_id, cooldown: int):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE serenity_stickies SET cooldown=%s WHERE channel_id=%s", (cooldown, str(channel_id)))
        conn.commit()
        conn.close()

    def set_sticky_message_id(self, channel_id, message_id):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE serenity_stickies SET message_id=%s WHERE channel_id=%s", (str(message_id), str(channel_id)))
        conn.commit()
        conn.close()

    def delete_sticky(self, channel_id):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_stickies WHERE channel_id=%s", (str(channel_id),))
        conn.commit()
        conn.close()

    def _row_to_dict(self, row) -> dict:
        return {
            "channel_id": row[0], "guild_id": row[1],
            "title": row[2], "content": row[3], "message_id": row[4],
            "enabled": bool(row[5]), "cooldown": row[6], "is_embed": bool(row[7])
        }

    # ── Posting helpers ──────────────────────────
    def _build_embed(self, sticky: dict, guild_name: str) -> discord.Embed:
        embed = discord.Embed(
            title=sticky["title"], # Will be None if not provided, which is fine
            description=sticky["content"],
            color=discord.Color.gold()
        )
        embed.set_footer(text=guild_name)
        return embed

    async def post_sticky(self, channel: discord.TextChannel):
        """Post or re-post a sticky message, deleting the old one first."""
        sticky = self.get_sticky(channel.id)
        if not sticky or not sticky["enabled"]:
            return

        # Delete old message
        if sticky["message_id"]:
            try:
                old = await channel.fetch_message(int(sticky["message_id"]))
                await old.delete()
            except:
                pass

        if sticky["is_embed"]:
            msg = await channel.send(embed=self._build_embed(sticky, channel.guild.name))
        else:
            msg = await channel.send(content=f"**{sticky['title']}**\n\n{sticky['content']}" if sticky['title'] else sticky['content'])
            
        self.set_sticky_message_id(channel.id, msg.id)

    # ── Listener ───────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        sticky = self.get_sticky(channel_id)
        if not sticky or not sticky["enabled"]:
            return

        self.msg_counter[channel_id] = self.msg_counter.get(channel_id, 0) + 1
        count = self.msg_counter[channel_id]

        if count % sticky["cooldown"] == 0:
            try:
                await self.post_sticky(message.channel)
            except Exception as e:
                print(f"Error refreshing sticky in {channel_id}: {e}")

    # ── Commands ───────────────────────────────
    sticky = app_commands.Group(name="sticky", description="Manage sticky messages")

    @sticky.command(name="add", description="Create or update the sticky message in this channel")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(is_embed="Whether to send as an embed (True) or normal text (False)")
    async def sticky_add(self, interaction: discord.Interaction, is_embed: bool = True):
        await interaction.response.send_modal(StickyCreateModal(self, interaction.channel, is_embed))

    @sticky.command(name="remove", description="Permanently delete the sticky message in this channel")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_remove(self, interaction: discord.Interaction):
        sticky = self.get_sticky(interaction.channel_id)
        if not sticky:
            await interaction.response.send_message("❌ No sticky message found in this channel.", ephemeral=True)
            return

        if sticky["message_id"]:
            try:
                msg = await interaction.channel.fetch_message(int(sticky["message_id"]))
                await msg.delete()
            except:
                pass

        self.delete_sticky(interaction.channel_id)
        await interaction.response.send_message("Sticky message deleted from this channel.", ephemeral=True)

    @sticky.command(name="enable", description="Enable the sticky message in this channel")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_enable(self, interaction: discord.Interaction):
        sticky = self.get_sticky(interaction.channel_id)
        if not sticky:
            await interaction.response.send_message("❌ No sticky message found in this channel.", ephemeral=True)
            return
        self.set_sticky_enabled(interaction.channel_id, True)
        await self.post_sticky(interaction.channel)
        await interaction.response.send_message("Sticky message enabled.", ephemeral=True)

    @sticky.command(name="disable", description="Disable the sticky message in this channel")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_disable(self, interaction: discord.Interaction):
        sticky = self.get_sticky(interaction.channel_id)
        if not sticky:
            await interaction.response.send_message("❌ No sticky message found in this channel.", ephemeral=True)
            return
        self.set_sticky_enabled(interaction.channel_id, False)
        await interaction.response.send_message("Sticky message disabled.", ephemeral=True)

    @sticky.command(name="cooldown", description="Set how many messages must pass before the sticky re-posts")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(messages="Number of messages before sticky re-sends (min: 1)")
    async def sticky_cooldown(self, interaction: discord.Interaction, messages: int):
        if messages < 1:
            await interaction.response.send_message("❌ Cooldown must be at least 1 message.", ephemeral=True)
            return
        sticky = self.get_sticky(interaction.channel_id)
        if not sticky:
            await interaction.response.send_message("❌ No sticky message found in this channel.", ephemeral=True)
            return
        self.set_sticky_cooldown(interaction.channel_id, messages)
        await interaction.response.send_message(f"Sticky will now re-send every `{messages}` message(s).", ephemeral=True)

    @sticky.command(name="list", description="List all sticky messages in this server")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_list(self, interaction: discord.Interaction):
        stickies = self.get_guild_stickies(interaction.guild_id)
        if not stickies:
            await interaction.response.send_message("No sticky messages exist in this server yet.", ephemeral=True)
            return

        embed = discord.Embed(title="📌 Sticky Messages", color=discord.Color.gold())
        for s in stickies:
            ch_mention = f"<#{s['channel_id']}>"
            status = "✅ Active" if s["enabled"] else "⏸ Paused"
            preview = (s["content"] or "")[:60] + ("..." if len(s["content"] or "") > 60 else "")
            embed.add_field(
                name=f"{s['title'] or 'No title'} | {ch_mention}",
                value=f"{status} · Cooldown: `{s['cooldown']}` msg(s)\n`{preview}`",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @sticky.command(name="preview", description="Preview the sticky message in this channel")
    @app_commands.default_permissions(manage_messages=True)
    async def sticky_preview(self, interaction: discord.Interaction):
        sticky = self.get_sticky(interaction.channel_id)
        if not sticky:
            await interaction.response.send_message("❌ No sticky message found in this channel.", ephemeral=True)
            return
        
        if sticky["is_embed"]:
            await interaction.response.send_message(embed=self._build_embed(sticky, interaction.guild.name), ephemeral=True)
        else:
            await interaction.response.send_message(content=f"**{sticky['title']}**\n\n{sticky['content']}" if sticky['title'] else sticky['content'], ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utility(bot))
