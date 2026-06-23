import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector



# ──────────────────────────────────────────────
# Persistent Button View
# ──────────────────────────────────────────────
class RRButtonView(discord.ui.View):
    def __init__(self, panel_id: int, entries: list, exclusive: bool):
        super().__init__(timeout=None)
        self.panel_id = panel_id
        style_map = {
            "primary":   discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary,
            "success":   discord.ButtonStyle.success,
            "danger":    discord.ButtonStyle.danger,
        }
        for (role_id, label, emoji, style) in entries:
            btn = discord.ui.Button(
                label=label,
                emoji=emoji or None,
                style=style_map.get(style, discord.ButtonStyle.primary),
                custom_id=f"rr_{panel_id}_{role_id}"
            )

            async def make_callback(r_id=role_id, p_id=panel_id, excl=exclusive):
                async def callback(interaction: discord.Interaction):
                    await handle_role_toggle(interaction, r_id, p_id, excl)
                return callback

            import asyncio
            btn.callback = asyncio.coroutine(make_callback()) if False else None  # placeholder

            self.add_item(btn)

        # Rebind callbacks properly
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                raw = item.custom_id  # e.g. rr_1_123456
                parts = raw.split("_")
                r_id = int(parts[2])
                p_id = int(parts[1])

                def bind(ri=r_id, pi=p_id, ex=exclusive):
                    async def cb(interaction: discord.Interaction):
                        await handle_role_toggle(interaction, ri, pi, ex)
                    return cb

                item.callback = bind()

# ──────────────────────────────────────────────
# Persistent Dropdown View
# ──────────────────────────────────────────────
class RRDropdown(discord.ui.Select):
    def __init__(self, panel_id: int, entries: list, exclusive: bool, max_roles: int):
        self.panel_id = panel_id
        self.exclusive = exclusive
        options = [
            discord.SelectOption(label=label, value=str(role_id), emoji=emoji or None)
            for (role_id, label, emoji, _style) in entries
        ]
        actual_max = 1 if exclusive else min(max_roles, len(options))
        super().__init__(
            placeholder="Select a role...",
            options=options,
            custom_id=f"rr_dropdown_{panel_id}",
            min_values=1,
            max_values=actual_max
        )

    async def callback(self, interaction: discord.Interaction):
        for value in self.values:
            role_id = int(value)
            await handle_role_toggle(interaction, role_id, self.panel_id, self.exclusive, already_responded=False)
            # After first response, we defer for subsequent ones
        # In case no message was sent (all roles already handled), send a summary
        if not interaction.response.is_done():
            await interaction.response.send_message("Done!", ephemeral=True)


class RRDropdownView(discord.ui.View):
    def __init__(self, panel_id: int, entries: list, exclusive: bool, max_roles: int):
        super().__init__(timeout=None)
        self.add_item(RRDropdown(panel_id, entries, exclusive, max_roles))


# ──────────────────────────────────────────────
# Shared toggle logic
# ──────────────────────────────────────────────
async def handle_role_toggle(interaction: discord.Interaction, role_id: int, panel_id: int, exclusive: bool, already_responded: bool = False):
    role = interaction.guild.get_role(role_id)
    if not role:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ That role no longer exists. Contact an admin.", ephemeral=True)
        return

    try:
        if exclusive:
            # Remove all other roles in this panel first
            conn = interaction.client.db.get_connection()
            c = conn.cursor()
            c.execute("SELECT role_id FROM serenity_rr_entries WHERE panel_id=%s", (panel_id,))
            all_role_ids = [int(r[0]) for r in c.fetchall()]
            conn.close()

            roles_to_remove = [
                interaction.guild.get_role(rid)
                for rid in all_role_ids
                if rid != role_id
            ]
            roles_to_remove = [r for r in roles_to_remove if r and r in interaction.user.roles]
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            msg = f"✅ Removed **{role.name}**."
        else:
            await interaction.user.add_roles(role)
            msg = f"✅ Added **{role.name}**."

        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)

    except discord.Forbidden:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ I don't have permission to manage that role.", ephemeral=True)
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ An error occurred: `{e}`", ephemeral=True)


# ──────────────────────────────────────────────
# Helper to build embed for a panel
# ──────────────────────────────────────────────
def build_panel_embed(title: str, description: str, entries: list, mode: str, exclusive: bool) -> discord.Embed:
    color = discord.Color.blurple()
    embed = discord.Embed(title=title, description=description or "", color=color)
    if entries:
        roles_text = "\n".join(
            f"{emoji or ''} **{label}**" for (_rid, label, emoji, _s) in entries
        )
        embed.add_field(name="Available Roles", value=roles_text, inline=False)
    embed.set_footer(text=f"Mode: {'Dropdown' if mode == 'dropdown' else 'Buttons'} | {'Exclusive — pick one' if exclusive else 'Multi-select'}")
    return embed


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────
class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_entries(self, panel_id: int) -> list:
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT role_id, label, emoji, style FROM serenity_rr_entries WHERE panel_id=%s", (panel_id,))
        entries = [(int(r[0]), r[1], r[2], r[3]) for r in c.fetchall()]
        conn.close()
        return entries

    def _get_panel(self, panel_id: int, guild_id: int):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, guild_id, channel_id, message_id, title, description, mode, exclusive, max_roles FROM serenity_rr_panels WHERE id=%s AND guild_id=%s", (panel_id, str(guild_id)))
        row = c.fetchone()
        conn.close()
        return row

    def _build_view(self, panel_id: int, mode: str, exclusive: bool, max_roles: int, entries: list):
        if mode == "dropdown":
            return RRDropdownView(panel_id, entries, exclusive, max_roles)
        return RRButtonView(panel_id, entries, exclusive)

    def restore_views(self):
        """Re-register all persistent views after bot restarts."""
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, mode, exclusive, max_roles FROM serenity_rr_panels")
        panels = c.fetchall()
        conn.close()
        for (panel_id, mode, exclusive, max_roles) in panels:
            entries = self._get_entries(panel_id)
            if not entries:
                continue
            view = self._build_view(panel_id, mode, bool(exclusive), max_roles, entries)
            self.bot.add_view(view)

    @commands.Cog.listener()
    async def on_ready(self):
        self.restore_views()

    # ────────── /rr group ──────────
    rr = app_commands.Group(name="rr", description="Advanced Reaction Roles system")

    @rr.command(name="create", description="Create a new reaction role panel")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(
        title="Title of the panel embed",
        description="Description shown on the panel embed",
        mode="'button' for buttons, 'dropdown' for a select menu",
        exclusive="If true, users can only pick ONE role from this panel",
        max_roles="Max roles a user can select at once (dropdown only, default 25)"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Buttons", value="button"),
        app_commands.Choice(name="Dropdown", value="dropdown"),
    ])
    async def rr_create(self, interaction: discord.Interaction,
                        title: str,
                        description: str = "",
                        mode: app_commands.Choice[str] = None,
                        exclusive: bool = False,
                        max_roles: int = 25):
        mode_val = mode.value if mode else "button"
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO serenity_rr_panels (guild_id, title, description, mode, exclusive, max_roles) VALUES (%s, %s, %s, %s, %s, %s)",
            (str(interaction.guild_id), title, description, mode_val, int(exclusive), max_roles)
        )
        panel_id = c.lastrowid
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Panel Created",
            description=f"Panel **#{panel_id}** created.\nNow use `/rr add_role {panel_id} <role>` to add roles, then `/rr post {panel_id}` to send it.",
            color=discord.Color.green()
        )
        embed.add_field(name="Title", value=f"`{title}`", inline=True)
        embed.add_field(name="Mode", value=f"`{'Dropdown' if mode_val == 'dropdown' else 'Buttons'}`", inline=True)
        embed.add_field(name="Exclusive", value=f"`{exclusive}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rr.command(name="add_role", description="Add a role to a reaction role panel")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(
        panel_id="ID of the panel to add the role to",
        role="The role to add",
        label="Button/dropdown label (default: role name)",
        emoji="Optional emoji to display",
        style="Button color style (ignored in dropdown mode)"
    )
    @app_commands.choices(style=[
        app_commands.Choice(name="Blue (Primary)", value="primary"),
        app_commands.Choice(name="Grey (Secondary)", value="secondary"),
        app_commands.Choice(name="Green (Success)", value="success"),
        app_commands.Choice(name="Red (Danger)", value="danger"),
    ])
    async def rr_add_role(self, interaction: discord.Interaction,
                          panel_id: int,
                          role: discord.Role,
                          label: str = None,
                          emoji: str = None,
                          style: app_commands.Choice[str] = None):
        panel = self._get_panel(panel_id, interaction.guild_id)
        if not panel:
            await interaction.response.send_message(f"❌ Panel `#{panel_id}` not found.", ephemeral=True)
            return

        entries = self._get_entries(panel_id)
        if len(entries) >= 25:
            await interaction.response.send_message("❌ A panel can have at most 25 roles.", ephemeral=True)
            return

        if any(str(e[0]) == str(role.id) for e in entries):
            await interaction.response.send_message(f"❌ {role.mention} is already in this panel.", ephemeral=True)
            return

        label_val = label or role.name
        style_val = style.value if style else "primary"

        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO serenity_rr_entries (panel_id, role_id, label, emoji, style) VALUES (%s, %s, %s, %s, %s)",
            (panel_id, str(role.id), label_val, emoji, style_val)
        )
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Added {role.mention} to panel **#{panel_id}** as `{label_val}`.", color=discord.Color.green()),
            ephemeral=True
        )

    @rr.command(name="remove_role", description="Remove a role from a reaction role panel")
    @app_commands.default_permissions(manage_roles=True)
    async def rr_remove_role(self, interaction: discord.Interaction, panel_id: int, role: discord.Role):
        panel = self._get_panel(panel_id, interaction.guild_id)
        if not panel:
            await interaction.response.send_message(f"❌ Panel `#{panel_id}` not found.", ephemeral=True)
            return

        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_rr_entries WHERE panel_id=%s AND role_id=%s", (panel_id, str(role.id)))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Removed {role.mention} from panel **#{panel_id}**.", color=discord.Color.green()),
            ephemeral=True
        )

    @rr.command(name="post", description="Post a reaction role panel to a channel")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(panel_id="ID of the panel to post", channel="Channel to post in (default: current channel)")
    async def rr_post(self, interaction: discord.Interaction, panel_id: int, channel: discord.TextChannel = None):
        panel = self._get_panel(panel_id, interaction.guild_id)
        if not panel:
            await interaction.response.send_message(f"❌ Panel `#{panel_id}` not found.", ephemeral=True)
            return

        _id, _guild, ch_id, msg_id, title, description, mode, exclusive, max_roles = panel
        entries = self._get_entries(panel_id)

        if not entries:
            await interaction.response.send_message("❌ Add at least one role to this panel before posting.", ephemeral=True)
            return

        target = channel or interaction.channel
        embed = build_panel_embed(title, description, entries, mode, bool(exclusive))
        view = self._build_view(panel_id, mode, bool(exclusive), max_roles, entries)

        # Register persistent view
        self.bot.add_view(view)

        # If already posted, try to edit the old message
        if msg_id and ch_id:
            try:
                old_channel = self.bot.get_channel(int(ch_id))
                if old_channel:
                    old_msg = await old_channel.fetch_message(int(msg_id))
                    await old_msg.edit(embed=embed, view=view)
                    await interaction.response.send_message("✅ Panel updated in place.", ephemeral=True)
                    return
            except:
                pass

        # Send new message
        msg = await target.send(embed=embed, view=view)

        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE serenity_rr_panels SET channel_id=%s, message_id=%s WHERE id=%s", (str(target.id), str(msg.id), panel_id))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ Panel **#{panel_id}** posted in {target.mention}.", ephemeral=True)

    @rr.command(name="list", description="List all reaction role panels in this server")
    @app_commands.default_permissions(manage_roles=True)
    async def rr_list(self, interaction: discord.Interaction):
        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, title, mode, exclusive, channel_id, message_id FROM serenity_rr_panels WHERE guild_id=%s", (str(interaction.guild_id),))
        panels = c.fetchall()
        conn.close()

        if not panels:
            await interaction.response.send_message("No reaction role panels exist yet. Use `/rr create` to make one.", ephemeral=True)
            return

        embed = discord.Embed(title="Reaction Role Panels", color=discord.Color.blurple())
        for (pid, title, mode, exclusive, ch_id, msg_id) in panels:
            entries = self._get_entries(pid)
            ch_mention = f"<#{ch_id}>" if ch_id else "Not posted"
            embed.add_field(
                name=f"Panel #{pid} — {title}",
                value=(
                    f"Mode: `{'Dropdown' if mode == 'dropdown' else 'Buttons'}`  |  "
                    f"Exclusive: `{bool(exclusive)}`\n"
                    f"Roles: `{len(entries)}`  |  Channel: {ch_mention}"
                ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @rr.command(name="delete", description="Delete a reaction role panel")
    @app_commands.default_permissions(manage_roles=True)
    async def rr_delete(self, interaction: discord.Interaction, panel_id: int):
        panel = self._get_panel(panel_id, interaction.guild_id)
        if not panel:
            await interaction.response.send_message(f"❌ Panel `#{panel_id}` not found.", ephemeral=True)
            return

        _id, _guild, ch_id, msg_id, *_ = panel

        # Try to delete the Discord message
        if msg_id and ch_id:
            try:
                ch = self.bot.get_channel(int(ch_id))
                if ch:
                    msg = await ch.fetch_message(int(msg_id))
                    await msg.delete()
            except:
                pass

        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM serenity_rr_entries WHERE panel_id=%s", (panel_id,))
        c.execute("DELETE FROM serenity_rr_panels WHERE id=%s", (panel_id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Panel **#{panel_id}** deleted.", color=discord.Color.green()),
            ephemeral=True
        )

    @rr.command(name="edit", description="Edit the title or description of a panel (and refresh it)")
    @app_commands.default_permissions(manage_roles=True)
    async def rr_edit(self, interaction: discord.Interaction, panel_id: int, title: str = None, description: str = None, exclusive: bool = None):
        panel = self._get_panel(panel_id, interaction.guild_id)
        if not panel:
            await interaction.response.send_message(f"❌ Panel `#{panel_id}` not found.", ephemeral=True)
            return

        _id, _guild, ch_id, msg_id, old_title, old_desc, mode, old_excl, max_roles = panel

        new_title = title or old_title
        new_desc = description if description is not None else old_desc
        new_excl = int(exclusive) if exclusive is not None else old_excl

        conn = self.bot.db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE serenity_rr_panels SET title=%s, description=%s, exclusive=%s WHERE id=%s", (new_title, new_desc, new_excl, panel_id))
        conn.commit()
        conn.close()

        # Refresh the posted message if it exists
        if msg_id and ch_id:
            try:
                ch = self.bot.get_channel(int(ch_id))
                if ch:
                    msg = await ch.fetch_message(int(msg_id))
                    entries = self._get_entries(panel_id)
                    embed = build_panel_embed(new_title, new_desc, entries, mode, bool(new_excl))
                    view = self._build_view(panel_id, mode, bool(new_excl), max_roles, entries)
                    self.bot.add_view(view)
                    await msg.edit(embed=embed, view=view)
            except:
                pass

        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Panel **#{panel_id}** updated.", color=discord.Color.green()),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
