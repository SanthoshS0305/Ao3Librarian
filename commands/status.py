"""Status command for viewing feed status."""
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


class StatusCommand(commands.Cog):
    """Status command for viewing feed information."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="status", description="Show feed status and information")
    @app_commands.describe(
        tag_id="The tag ID to check",
        subscription_id="Alternatively, use the subscription ID"
    )
    async def status_slash(
        self,
        interaction: discord.Interaction,
        tag_id: str = None,
        subscription_id: int = None
    ):
        """Slash command to show feed status."""
        # Defer response immediately to avoid interaction timeout
        await interaction.response.defer(ephemeral=True)
        
        if not tag_id and not subscription_id:
            await interaction.followup.send(
                "❌ Please provide either a tag ID or subscription ID.",
                ephemeral=True
            )
            return
        
        try:
            if subscription_id:
                subscription = await db.get_subscription_by_id(subscription_id)
                if not subscription:
                    await interaction.followup.send(
                        f"❌ Subscription ID {subscription_id} not found.",
                        ephemeral=True
                    )
                    return
                tag_id_value = subscription["tag_id"]
                feed = await db.get_feed_by_tag_id(tag_id_value)
            else:
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
                tag_id_value = extracted_tag_id
            
            # Get all subscriptions for this feed
            subscriptions = await db.get_subscriptions_by_feed(feed["id"])
            
            # Build embed
            embed = discord.Embed(
                title="Feed Status",
                description=f"**Tag ID:** {tag_id_value}\n**Feed URL:** https://archiveofourown.org/tags/{tag_id_value}/feed.atom",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Feed ID",
                value=str(feed["id"]),
                inline=True
            )
            
            embed.add_field(
                name="Subscriptions",
                value=str(len(subscriptions)),
                inline=True
            )
            
            if feed["last_updated"]:
                embed.add_field(
                    name="Last Updated",
                    value=feed["last_updated"].strftime("%Y-%m-%d %H:%M:%S UTC"),
                    inline=False
                )
            
            if feed["last_entry_id"]:
                embed.add_field(
                    name="Last Entry ID",
                    value=feed["last_entry_id"][:50] + "..." if len(feed["last_entry_id"]) > 50 else feed["last_entry_id"],
                    inline=False
                )
            
            if feed.get("created_at"):
                embed.add_field(
                    name="Created",
                    value=feed["created_at"].strftime("%Y-%m-%d"),
                    inline=True
                )
            
            # List subscriptions
            if subscriptions:
                sub_list = []
                for sub in subscriptions[:10]:
                    channel_mention = f"<#{sub['channel_id']}>"
                    excluded_tags = await db.get_excluded_tags(sub["id"])
                    excluded_count = len(excluded_tags)
                    sub_list.append(
                        f"**ID {sub['id']}:** {channel_mention} ({excluded_count} excluded tags)"
                    )
                
                if len(subscriptions) > 10:
                    sub_list.append(f"\n*...and {len(subscriptions) - 10} more*")
                
                embed.add_field(
                    name="Subscribed Channels",
                    value="\n".join(sub_list) or "None",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=False)
        
        except Exception as e:
            logger.error(f"Error in status command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred while getting status: {str(e)}",
                ephemeral=True
            )
    
    @commands.command(name="status")
    async def status_prefix(
        self,
        ctx: commands.Context,
        tag_id: str = None,
        subscription_id: int = None
    ):
        """Prefix command to show feed status."""
        if not tag_id and not subscription_id:
            await ctx.send("❌ Please provide either a tag ID or subscription ID.")
            return
        
        try:
            if subscription_id:
                subscription = await db.get_subscription_by_id(subscription_id)
                if not subscription:
                    await ctx.send(f"❌ Subscription ID {subscription_id} not found.")
                    return
                tag_id_value = subscription["tag_id"]
                feed = await db.get_feed_by_tag_id(tag_id_value)
            else:
                extracted_tag_id = extract_tag_id(tag_id)
                if not extracted_tag_id or not validate_tag_id(extracted_tag_id):
                    await ctx.send("❌ Invalid tag ID or feed URL.")
                    return
                feed = await db.get_feed_by_tag_id(extracted_tag_id)
                if not feed:
                    await ctx.send(f"❌ Feed not found: {extracted_tag_id}")
                    return
                tag_id_value = extracted_tag_id
            
            subscriptions = await db.get_subscriptions_by_feed(feed["id"])
            
            message_parts = [
                f"**Feed Status:**\n",
                f"**Tag ID:** {tag_id_value}\n",
                f"**Feed URL:** https://archiveofourown.org/tags/{tag_id_value}/feed.atom\n",
                f"**Feed ID:** {feed['id']}\n",
                f"**Subscriptions:** {len(subscriptions)}\n"
            ]
            
            if feed["last_updated"]:
                message_parts.append(f"**Last Updated:** {feed['last_updated'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            
            if feed.get("created_at"):
                message_parts.append(f"**Created:** {feed['created_at'].strftime('%Y-%m-%d')}\n")
            
            if subscriptions:
                message_parts.append("\n**Subscribed Channels:**\n")
                for sub in subscriptions[:10]:
                    excluded_tags = await db.get_excluded_tags(sub["id"])
                    excluded_count = len(excluded_tags)
                    message_parts.append(
                        f"  ID {sub['id']}: <#{sub['channel_id']}> ({excluded_count} excluded tags)\n"
                    )
                if len(subscriptions) > 10:
                    message_parts.append(f"  ...and {len(subscriptions) - 10} more\n")
            
            await ctx.send("".join(message_parts))
        
        except Exception as e:
            logger.error(f"Error in status command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while getting status: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(StatusCommand(bot))
