"""Track command for subscribing channels to RSS feeds."""
import discord
from discord import app_commands
from discord.ext import commands
import logging
import re
from database import db
from config import config

logger = logging.getLogger(__name__)

# AO3 RSS feed URL pattern - extract tag_id
AO3_FEED_PATTERN = re.compile(r'^https?://archiveofourown\.org/tags/([^/]+)/feed\.atom(\?.*)?$')
# Tag ID pattern (alphanumeric, hyphens, underscores, max 100 chars)
TAG_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,100}$')


def extract_tag_id(input_str: str) -> Optional[str]:
    """Extract tag_id from input (handles both full URL and just tag_id)."""
    input_str = input_str.strip()
    
    # Try full URL pattern first
    match = AO3_FEED_PATTERN.match(input_str)
    if match:
        return match.group(1)
    
    # Try just tag_id pattern
    if TAG_ID_PATTERN.match(input_str):
        return input_str
    
    return None


def validate_tag_id(tag_id: str) -> bool:
    """Validate that tag_id is valid format."""
    return bool(TAG_ID_PATTERN.match(tag_id))


class TrackCommand(commands.Cog):
    """Track command for subscribing to RSS feeds."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="track", description="Subscribe a channel to an AO3 RSS feed")
    @app_commands.describe(
        tag_id="The AO3 tag ID or full feed URL (e.g., 541570 or https://archiveofourown.org/tags/541570/feed.atom)",
        channel="The channel to send notifications to (defaults to current channel)"
    )
    async def track_slash(
        self,
        interaction: discord.Interaction,
        tag_id: str,
        channel: discord.TextChannel = None
    ):
        """Slash command to track a feed."""
        target_channel = channel or interaction.channel
        
        # Extract tag_id from input
        extracted_tag_id = extract_tag_id(tag_id)
        if not extracted_tag_id or not validate_tag_id(extracted_tag_id):
            await interaction.response.send_message(
                "❌ Invalid AO3 tag ID or feed URL. Must be:\n"
                "- A tag ID (alphanumeric, hyphens, underscores, max 100 chars), or\n"
                "- A full feed URL: `https://archiveofourown.org/tags/{tag_id}/feed.atom`",
                ephemeral=True
            )
            return
        
        # Check permissions if required by server
        require_perms = await db.get_require_permissions(interaction.guild.id)
        if require_perms:
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ You need the `manage_channels` permission to track feeds in this server.",
                    ephemeral=True
                )
                return
        
        # Check subscription limit
        existing_subs = await db.get_subscriptions_by_channel(target_channel.id)
        if len(existing_subs) >= config.MAX_SUBSCRIPTIONS_PER_CHANNEL:
            await interaction.response.send_message(
                f"❌ Channel {target_channel.mention} has reached the maximum of {config.MAX_SUBSCRIPTIONS_PER_CHANNEL} subscriptions.",
                ephemeral=True
            )
            return
        
        # Check permissions
        if not target_channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {target_channel.mention}",
                ephemeral=True
            )
            return
        
        try:
            # Get or create feed
            feed_id = await db.get_or_create_feed(extracted_tag_id)
            
            # Check if subscription already exists
            if await db.subscription_exists(feed_id, target_channel.id):
                await interaction.response.send_message(
                    f"⚠️ {target_channel.mention} is already tracking this feed.",
                    ephemeral=True
                )
                return
            
            # Create subscription
            subscription_id = await db.create_subscription(
                feed_id,
                target_channel.id,
                interaction.guild.id
            )
            
            await interaction.response.send_message(
                f"✅ Successfully subscribed {target_channel.mention} to feed!\n"
                f"**Tag ID:** {extracted_tag_id}\n"
                f"**Subscription ID:** {subscription_id}",
                ephemeral=False
            )
            logger.info(f"Created subscription: feed_id={feed_id}, channel_id={target_channel.id}, subscription_id={subscription_id}, user_id={interaction.user.id}")
        
        except Exception as e:
            logger.error(f"Error in track command: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ An error occurred while tracking the feed: {str(e)}",
                ephemeral=True
            )
    
    @commands.command(name="track")
    async def track_prefix(self, ctx: commands.Context, tag_id: str, channel: discord.TextChannel = None):
        """Prefix command to track a feed."""
        target_channel = channel or ctx.channel
        
        # Extract tag_id from input
        extracted_tag_id = extract_tag_id(tag_id)
        if not extracted_tag_id or not validate_tag_id(extracted_tag_id):
            await ctx.send(
                "❌ Invalid AO3 tag ID or feed URL. Must be:\n"
                "- A tag ID (alphanumeric, hyphens, underscores, max 100 chars), or\n"
                "- A full feed URL: `https://archiveofourown.org/tags/{tag_id}/feed.atom`"
            )
            return
        
        # Check permissions if required by server
        require_perms = await db.get_require_permissions(ctx.guild.id)
        if require_perms:
            if not ctx.author.guild_permissions.manage_channels:
                await ctx.send("❌ You need the `manage_channels` permission to track feeds in this server.")
                return
        
        # Check subscription limit
        existing_subs = await db.get_subscriptions_by_channel(target_channel.id)
        if len(existing_subs) >= config.MAX_SUBSCRIPTIONS_PER_CHANNEL:
            await ctx.send(f"❌ Channel {target_channel.mention} has reached the maximum of {config.MAX_SUBSCRIPTIONS_PER_CHANNEL} subscriptions.")
            return
        
        # Check permissions
        if not target_channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(f"❌ I don't have permission to send messages in {target_channel.mention}")
            return
        
        try:
            # Get or create feed
            feed_id = await db.get_or_create_feed(extracted_tag_id)
            
            # Check if subscription already exists
            if await db.subscription_exists(feed_id, target_channel.id):
                await ctx.send(f"⚠️ {target_channel.mention} is already tracking this feed.")
                return
            
            # Create subscription
            subscription_id = await db.create_subscription(
                feed_id,
                target_channel.id,
                ctx.guild.id
            )
            
            await ctx.send(
                f"✅ Successfully subscribed {target_channel.mention} to feed!\n"
                f"**Tag ID:** {extracted_tag_id}\n"
                f"**Subscription ID:** {subscription_id}"
            )
            logger.info(f"Created subscription: feed_id={feed_id}, channel_id={target_channel.id}, subscription_id={subscription_id}, user_id={ctx.author.id}")
        
        except Exception as e:
            logger.error(f"Error in track command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while tracking the feed: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(TrackCommand(bot))
