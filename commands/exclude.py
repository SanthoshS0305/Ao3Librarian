"""Exclude command for adding tag exclusions to subscriptions."""
import discord
from discord import app_commands
from discord.ext import commands
import logging
import re
from urllib.parse import unquote
from database import db

logger = logging.getLogger(__name__)

# Pattern to extract tag name from URL
TAG_URL_PATTERN = re.compile(r'https?://archiveofourown\.org/tags/([^/]+)')


def extract_tag_name_from_url(tag_url: str) -> str:
    """Extract and clean tag name from URL.
    
    Handles:
    - https://archiveofourown.org/tags/TagName
    - https://archiveofourown.org/tags/TagName/works (removes /works)
    - URL-encoded tag names
    """
    # Try to extract from URL
    match = TAG_URL_PATTERN.match(tag_url.strip())
    if match:
        tag_name = unquote(match.group(1))
        return tag_name
    
    # If no match, assume it's already a tag name
    return tag_url.strip()


class ExcludeCommand(commands.Cog):
    """Exclude command for managing tag exclusions."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="exclude", description="Add a tag name to exclusion list for a subscription")
    @app_commands.describe(
        subscription_id="The subscription ID (use /list to find it)",
        tag_url="The tag URL or tag name to exclude (e.g., https://archiveofourown.org/tags/SomeTag or just 'SomeTag')"
    )
    async def exclude_slash(
        self,
        interaction: discord.Interaction,
        subscription_id: int,
        tag_url: str
    ):
        """Slash command to exclude a tag."""
        try:
            # Verify subscription exists and belongs to this server
            subscription = await db.get_subscription_by_id(subscription_id)
            if not subscription:
                await interaction.response.send_message(
                    f"❌ Subscription ID {subscription_id} not found.",
                    ephemeral=True
                )
                return
            
            # Check if user has permission (must be in the same server)
            if interaction.guild.id != subscription["server_id"]:
                await interaction.response.send_message(
                    "❌ You can only manage subscriptions in your own server.",
                    ephemeral=True
                )
                return
            
            # Extract and clean tag name
            tag_name = extract_tag_name_from_url(tag_url)
            if len(tag_name) > 500:
                await interaction.response.send_message(
                    "❌ Tag name is too long (max 500 characters).",
                    ephemeral=True
                )
                return
            
            # Add excluded tag
            added = await db.add_excluded_tag(subscription_id, tag_name)
            
            if added:
                await interaction.response.send_message(
                    f"✅ Added tag to exclusion list.\n"
                    f"**Subscription ID:** {subscription_id}\n"
                    f"**Excluded Tag:** {tag_name}",
                    ephemeral=False
                )
                logger.info(f"Added excluded tag: subscription_id={subscription_id}, tag_name={tag_name}, user_id={interaction.user.id}")
            else:
                await interaction.response.send_message(
                    f"⚠️ Tag is already in the exclusion list.",
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Error in exclude command: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ An error occurred while adding exclusion: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="unexclude", description="Remove a tag name from exclusion list")
    @app_commands.describe(
        subscription_id="The subscription ID",
        tag_url="The tag URL or tag name to remove from exclusions"
    )
    async def unexclude_slash(
        self,
        interaction: discord.Interaction,
        subscription_id: int,
        tag_url: str
    ):
        """Slash command to remove an exclusion."""
        try:
            # Verify subscription exists and belongs to this server
            subscription = await db.get_subscription_by_id(subscription_id)
            if not subscription:
                await interaction.response.send_message(
                    f"❌ Subscription ID {subscription_id} not found.",
                    ephemeral=True
                )
                return
            
            if interaction.guild.id != subscription["server_id"]:
                await interaction.response.send_message(
                    "❌ You can only manage subscriptions in your own server.",
                    ephemeral=True
                )
                return
            
            # Extract and clean tag name
            tag_name = extract_tag_name_from_url(tag_url)
            
            # Remove excluded tag
            removed = await db.remove_excluded_tag(subscription_id, tag_name)
            
            if removed:
                await interaction.response.send_message(
                    f"✅ Removed tag from exclusion list.\n"
                    f"**Subscription ID:** {subscription_id}\n"
                    f"**Tag:** {tag_name}",
                    ephemeral=False
                )
                logger.info(f"Removed excluded tag: subscription_id={subscription_id}, tag_name={tag_name}, user_id={interaction.user.id}")
            else:
                await interaction.response.send_message(
                    f"⚠️ Tag was not in the exclusion list.",
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Error in unexclude command: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ An error occurred while removing exclusion: {str(e)}",
                ephemeral=True
            )
    
    @commands.command(name="exclude")
    async def exclude_prefix(self, ctx: commands.Context, subscription_id: int, tag_url: str):
        """Prefix command to exclude a tag."""
        try:
            subscription = await db.get_subscription_by_id(subscription_id)
            if not subscription:
                await ctx.send(f"❌ Subscription ID {subscription_id} not found.")
                return
            
            if ctx.guild.id != subscription["server_id"]:
                await ctx.send("❌ You can only manage subscriptions in your own server.")
                return
            
            tag_name = extract_tag_name_from_url(tag_url)
            if len(tag_name) > 500:
                await ctx.send("❌ Tag name is too long (max 500 characters).")
                return
            
            added = await db.add_excluded_tag(subscription_id, tag_name)
            
            if added:
                await ctx.send(
                    f"✅ Added tag to exclusion list.\n"
                    f"**Subscription ID:** {subscription_id}\n"
                    f"**Excluded Tag:** {tag_name}"
                )
                logger.info(f"Added excluded tag: subscription_id={subscription_id}, tag_name={tag_name}, user_id={ctx.author.id}")
            else:
                await ctx.send("⚠️ Tag is already in the exclusion list.")
        
        except Exception as e:
            logger.error(f"Error in exclude command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while adding exclusion: {str(e)}")
    
    @commands.command(name="unexclude")
    async def unexclude_prefix(self, ctx: commands.Context, subscription_id: int, tag_url: str):
        """Prefix command to remove an exclusion."""
        try:
            subscription = await db.get_subscription_by_id(subscription_id)
            if not subscription:
                await ctx.send(f"❌ Subscription ID {subscription_id} not found.")
                return
            
            if ctx.guild.id != subscription["server_id"]:
                await ctx.send("❌ You can only manage subscriptions in your own server.")
                return
            
            tag_name = extract_tag_name_from_url(tag_url)
            
            removed = await db.remove_excluded_tag(subscription_id, tag_name)
            
            if removed:
                await ctx.send(
                    f"✅ Removed tag from exclusion list.\n"
                    f"**Subscription ID:** {subscription_id}\n"
                    f"**Tag:** {tag_name}"
                )
                logger.info(f"Removed excluded tag: subscription_id={subscription_id}, tag_name={tag_name}, user_id={ctx.author.id}")
            else:
                await ctx.send("⚠️ Tag was not in the exclusion list.")
        
        except Exception as e:
            logger.error(f"Error in unexclude command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while removing exclusion: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(ExcludeCommand(bot))
