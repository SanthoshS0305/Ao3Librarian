"""Untrack command for unsubscribing channels from RSS feeds."""
import discord
from discord import app_commands
from discord.ext import commands
import logging
import re
from database import db

# Import tag extraction functions (avoid circular import by defining here)
AO3_FEED_PATTERN = re.compile(r'^https?://archiveofourown\.org/tags/([^/]+)/feed\.atom(\?.*)?$')
TAG_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,100}$')


def extract_tag_id(input_str: str):
    """Extract tag_id from input (handles both full URL and just tag_id)."""
    input_str = input_str.strip()
    match = AO3_FEED_PATTERN.match(input_str)
    if match:
        return match.group(1)
    if TAG_ID_PATTERN.match(input_str):
        return input_str
    return None


def validate_tag_id(tag_id: str) -> bool:
    """Validate that tag_id is valid format."""
    return bool(TAG_ID_PATTERN.match(tag_id))

logger = logging.getLogger(__name__)


class UntrackCommand(commands.Cog):
    """Untrack command for unsubscribing from RSS feeds."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="untrack", description="Unsubscribe a channel from an RSS feed")
    @app_commands.describe(
        tag_id="The tag ID or feed URL to untrack",
        channel="The channel to untrack (defaults to current channel)",
        subscription_id="Alternatively, use the subscription ID"
    )
    async def untrack_slash(
        self,
        interaction: discord.Interaction,
        tag_id: str = None,
        channel: discord.TextChannel = None,
        subscription_id: int = None
    ):
        """Slash command to untrack a feed."""
        # Defer response immediately to avoid interaction timeout
        await interaction.response.defer(ephemeral=True)
        
        if not tag_id and not subscription_id:
            await interaction.followup.send(
                "❌ Please provide either a tag ID/feed URL or subscription ID.",
                ephemeral=True
            )
            return
        
        target_channel = channel or interaction.channel
        
        # Check permissions if required by server
        require_perms = await db.get_require_permissions(interaction.guild.id)
        if require_perms:
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send(
                    "❌ You need the `manage_channels` permission to untrack feeds in this server.",
                    ephemeral=True
                )
                return
        
        try:
            if subscription_id:
                # Use subscription ID
                subscription = await db.get_subscription_by_id(subscription_id)
                if not subscription:
                    await interaction.followup.send(
                        f"❌ Subscription ID {subscription_id} not found.",
                        ephemeral=True
                    )
                    return
                
                if subscription["channel_id"] != target_channel.id:
                    await interaction.followup.send(
                        f"❌ Subscription {subscription_id} is not for {target_channel.mention}.",
                        ephemeral=True
                    )
                    return
                
                feed_id = subscription["feed_id"]
                tag_id_value = subscription["tag_id"]
            else:
                # Use tag_id
                extracted_tag_id = extract_tag_id(tag_id)
                if not extracted_tag_id or not validate_tag_id(extracted_tag_id):
                    await interaction.followup.send(
                        "❌ Invalid tag ID or feed URL.",
                        ephemeral=True
                    )
                    return
                
                feed = await db.get_feed_by_tag_id(extracted_tag_id)
                if not feed:
                    await interaction.followup.send(
                        f"❌ Feed not found: {extracted_tag_id}",
                        ephemeral=True
                    )
                    return
                feed_id = feed["id"]
                tag_id_value = extracted_tag_id
            
            # Delete subscription
            deleted = await db.delete_subscription(feed_id, target_channel.id)
            
            if deleted:
                await interaction.followup.send(
                    f"✅ Successfully unsubscribed {target_channel.mention} from feed.\n"
                    f"**Tag ID:** {tag_id_value}",
                    ephemeral=False
                )
                logger.info(f"Deleted subscription: feed_id={feed_id}, channel_id={target_channel.id}, user_id={interaction.user.id}")
            else:
                await interaction.followup.send(
                    f"⚠️ {target_channel.mention} is not tracking this feed.",
                    ephemeral=True
                )
        
        except Exception as e:
            logger.error(f"Error in untrack command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred while untracking the feed: {str(e)}",
                ephemeral=True
            )
    
    @commands.command(name="untrack")
    async def untrack_prefix(
        self,
        ctx: commands.Context,
        tag_id: str = None,
        channel: discord.TextChannel = None,
        subscription_id: int = None
    ):
        """Prefix command to untrack a feed."""
        if not tag_id and not subscription_id:
            await ctx.send("❌ Please provide either a tag ID/feed URL or subscription ID.")
            return
        
        target_channel = channel or ctx.channel
        
        # Check permissions if required by server
        require_perms = await db.get_require_permissions(ctx.guild.id)
        if require_perms:
            if not ctx.author.guild_permissions.manage_channels:
                await ctx.send("❌ You need the `manage_channels` permission to untrack feeds in this server.")
                return
        
        try:
            if subscription_id:
                subscription = await db.get_subscription_by_id(subscription_id)
                if not subscription:
                    await ctx.send(f"❌ Subscription ID {subscription_id} not found.")
                    return
                
                if subscription["channel_id"] != target_channel.id:
                    await ctx.send(f"❌ Subscription {subscription_id} is not for {target_channel.mention}.")
                    return
                
                feed_id = subscription["feed_id"]
                tag_id_value = subscription["tag_id"]
            else:
                extracted_tag_id = extract_tag_id(tag_id)
                if not extracted_tag_id or not validate_tag_id(extracted_tag_id):
                    await ctx.send("❌ Invalid tag ID or feed URL.")
                    return
                
                feed = await db.get_feed_by_tag_id(extracted_tag_id)
                if not feed:
                    await ctx.send(f"❌ Feed not found: {extracted_tag_id}")
                    return
                feed_id = feed["id"]
                tag_id_value = extracted_tag_id
            
            deleted = await db.delete_subscription(feed_id, target_channel.id)
            
            if deleted:
                await ctx.send(
                    f"✅ Successfully unsubscribed {target_channel.mention} from feed.\n"
                    f"**Tag ID:** {tag_id_value}"
                )
                logger.info(f"Deleted subscription: feed_id={feed_id}, channel_id={target_channel.id}, user_id={ctx.author.id}")
            else:
                await ctx.send(f"⚠️ {target_channel.mention} is not tracking this feed.")
        
        except Exception as e:
            logger.error(f"Error in untrack command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while untracking the feed: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(UntrackCommand(bot))
