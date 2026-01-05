"""Settings command for managing server settings."""
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database import db

logger = logging.getLogger(__name__)


def parse_boolean(value: str) -> bool:
    """Parse various boolean string representations."""
    value_lower = value.lower().strip()
    true_values = ['true', '1', 'yes', 'on', 'enable', 'enabled']
    false_values = ['false', '0', 'no', 'off', 'disable', 'disabled']
    
    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    else:
        raise ValueError(f"Invalid boolean value: {value}")


class SettingsCommand(commands.Cog):
    """Settings command for managing server configuration."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="settings", description="Manage server settings")
    @app_commands.describe(
        setting="The setting to change (currently only 'require_permissions')",
        value="The value (true/false, on/off, yes/no, 1/0)"
    )
    async def settings_slash(
        self,
        interaction: discord.Interaction,
        setting: str = None,
        value: str = None
    ):
        """Slash command to manage settings."""
        # Check user has manage_channels permission (always required)
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ You need the `manage_channels` permission to change settings.",
                ephemeral=True
            )
            return
        
        if setting and value:
            # Setting a value
            if setting.lower() == "require_permissions":
                try:
                    bool_value = parse_boolean(value)
                    await db.set_require_permissions(
                        interaction.guild.id,
                        bool_value,
                        interaction.user.id
                    )
                    
                    status = "enabled" if bool_value else "disabled"
                    await interaction.response.send_message(
                        f"✅ Permission requirement {status} for this server.\n"
                        f"**Setting:** `require_permissions` = `{bool_value}`",
                        ephemeral=False
                    )
                    logger.info(f"Updated require_permissions for server {interaction.guild.id}: {bool_value}, user_id={interaction.user.id}")
                except ValueError as e:
                    await interaction.response.send_message(
                        f"❌ Invalid value. Use: true/false, on/off, yes/no, 1/0",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    f"❌ Unknown setting: {setting}. Available: `require_permissions`",
                    ephemeral=True
                )
        else:
            # Show current settings
            settings = await db.get_server_settings(interaction.guild.id)
            
            embed = discord.Embed(
                title="Server Settings",
                color=discord.Color.blue()
            )
            
            if settings:
                require_perms = settings.get("require_permissions", False)
                updated_at = settings.get("updated_at")
                updated_by = settings.get("updated_by")
                
                embed.add_field(
                    name="Require Permissions",
                    value="✅ Enabled" if require_perms else "❌ Disabled",
                    inline=False
                )
                
                if updated_at:
                    embed.add_field(
                        name="Last Updated",
                        value=updated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        inline=True
                    )
                
                if updated_by:
                    embed.add_field(
                        name="Updated By",
                        value=f"<@{updated_by}>",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="Require Permissions",
                    value="❌ Disabled (default)",
                    inline=False
                )
                embed.add_field(
                    name="Note",
                    value="No custom settings configured. All settings use defaults.",
                    inline=False
                )
            
            embed.set_footer(text="Use /settings require_permissions <value> to change")
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @commands.group(name="settings", invoke_without_command=True)
    async def settings_prefix(self, ctx: commands.Context):
        """Prefix command group for settings."""
        # Check user has manage_channels permission
        if not ctx.author.guild_permissions.manage_channels:
            await ctx.send("❌ You need the `manage_channels` permission to view settings.")
            return
        
        settings = await db.get_server_settings(ctx.guild.id)
        
        message_parts = ["**Server Settings:**\n"]
        
        if settings:
            require_perms = settings.get("require_permissions", False)
            message_parts.append(f"**Require Permissions:** {'✅ Enabled' if require_perms else '❌ Disabled'}\n")
            
            if settings.get("updated_at"):
                message_parts.append(f"**Last Updated:** {settings['updated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        else:
            message_parts.append("**Require Permissions:** ❌ Disabled (default)\n")
            message_parts.append("_No custom settings configured._\n")
        
        message_parts.append("\nUse `!settings require_permissions <true/false>` to change")
        
        await ctx.send("".join(message_parts))
    
    @settings_prefix.command(name="require_permissions")
    async def settings_require_permissions(self, ctx: commands.Context, value: str):
        """Set require_permissions setting."""
        if not ctx.author.guild_permissions.manage_channels:
            await ctx.send("❌ You need the `manage_channels` permission to change settings.")
            return
        
        try:
            bool_value = parse_boolean(value)
            await db.set_require_permissions(
                ctx.guild.id,
                bool_value,
                ctx.author.id
            )
            
            status = "enabled" if bool_value else "disabled"
            await ctx.send(
                f"✅ Permission requirement {status} for this server.\n"
                f"**Setting:** `require_permissions` = `{bool_value}`"
            )
            logger.info(f"Updated require_permissions for server {ctx.guild.id}: {bool_value}, user_id={ctx.author.id}")
        except ValueError:
            await ctx.send("❌ Invalid value. Use: true/false, on/off, yes/no, 1/0")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(SettingsCommand(bot))
