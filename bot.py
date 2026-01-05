"""Main Discord bot for AO3 RSS Tracker."""
import discord
from discord.ext import commands, tasks
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Set

from config import config
from database import db
from feed_parser import feed_parser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AO3TrackerBot(commands.Bot):
    """Discord bot for tracking AO3 RSS feeds."""
    
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = config.MESSAGE_CONTENT_INTENT
        intents.guilds = True
        
        super().__init__(
            command_prefix=config.COMMAND_PREFIX,
            intents=intents,
            help_command=None  # Disable default help command
        )
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")
        
        # Connect to database
        await db.connect()
        
        # Load command cogs
        await self.load_extension("commands.track")
        await self.load_extension("commands.untrack")
        await self.load_extension("commands.exclude")
        await self.load_extension("commands.list")
        await self.load_extension("commands.status")
        await self.load_extension("commands.settings")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")
        
        # Start polling task
        self.poll_feeds.start()
        logger.info("Feed polling task started")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guild(s)")
    
    async def close(self):
        """Called when the bot is shutting down."""
        logger.info("Shutting down bot...")
        self.poll_feeds.cancel()
        await db.close()
        await super().close()
    
    def create_entry_embed(self, entry: Dict) -> discord.Embed:
        """Create a Discord embed for a feed entry."""
        embed = discord.Embed(
            title=entry["title"],
            url=entry["link"],
            description=entry.get("summary_html", "")[:2000] if entry.get("summary_html") else "No summary",
            color=discord.Color.blue(),
            timestamp=entry.get("updated") or entry.get("published") or datetime.utcnow()
        )
        
        # Add author
        embed.set_author(name=entry.get("author", "Unknown"))
        
        # Add metadata fields
        if entry.get("words"):
            embed.add_field(name="Words", value=f"{entry['words']:,}", inline=True)
        
        if entry.get("chapters"):
            embed.add_field(name="Chapters", value=entry["chapters"], inline=True)
        
        if entry.get("rating"):
            embed.add_field(name="Rating", value=entry["rating"], inline=True)
        
        if entry.get("language"):
            embed.add_field(name="Language", value=entry["language"], inline=True)
        
        # Add tags (truncate if too long)
        if entry.get("relationships"):
            relationships = ", ".join(entry["relationships"][:5])
            if len(entry["relationships"]) > 5:
                relationships += f" (+{len(entry['relationships']) - 5} more)"
            embed.add_field(name="Relationships", value=relationships[:1024], inline=False)
        
        if entry.get("characters"):
            characters = ", ".join(entry["characters"][:5])
            if len(entry["characters"]) > 5:
                characters += f" (+{len(entry['characters']) - 5} more)"
            embed.add_field(name="Characters", value=characters[:1024], inline=False)
        
        if entry.get("additional_tags"):
            tags = ", ".join(entry["additional_tags"][:10])
            if len(entry["additional_tags"]) > 10:
                tags += f" (+{len(entry['additional_tags']) - 10} more)"
            embed.add_field(name="Tags", value=tags[:1024], inline=False)
        
        # Add warnings if present
        if entry.get("warnings"):
            warnings = ", ".join(entry["warnings"])
            embed.add_field(name="Warnings", value=warnings[:1024], inline=False)
        
        embed.set_footer(text="Archive of Our Own")
        
        return embed
    
    async def send_entry_notification(self, entry: Dict, channel_id: int):
        """Send a notification for an entry to a channel."""
        try:
            channel = self.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return False
            
            # Check permissions
            if not channel.permissions_for(channel.guild.me).send_messages:
                logger.warning(f"No permission to send messages in channel {channel_id}")
                return False
            
            embed = self.create_entry_embed(entry)
            await channel.send(embed=embed)
            logger.info(f"Sent notification for entry {entry['id']} to channel {channel_id}")
            return True
        
        except discord.Forbidden:
            logger.warning(f"Forbidden to send message to channel {channel_id}")
            return False
        except Exception as e:
            logger.error(f"Error sending notification to channel {channel_id}: {e}", exc_info=True)
            return False
    
    @tasks.loop(seconds=config.POLLING_INTERVAL)
    async def poll_feeds(self):
        """Background task to poll all feeds for updates."""
        logger.info("Starting feed polling cycle...")
        
        try:
            # Get all unique feeds
            feeds = await db.get_all_feeds()
            logger.info(f"Polling {len(feeds)} unique feed(s)")
            
            for feed in feeds:
                try:
                    feed_id = feed["id"]
                    tag_id = feed["tag_id"]
                    last_entry_id = feed.get("last_entry_id")
                    
                    # Construct feed URL from tag_id
                    feed_url = feed_parser.construct_feed_url(tag_id)
                    
                    logger.info(f"Fetching feed: {feed_url} (tag_id: {tag_id})")
                    
                    # Fetch and parse feed
                    feed_data = await feed_parser.fetch_and_parse(feed_url)
                    if not feed_data:
                        logger.warning(f"Failed to fetch feed: {feed_url}")
                        continue
                    
                    entries = feed_data["entries"]
                    if not entries:
                        logger.info(f"No entries found in feed: {feed_url}")
                        continue
                    
                    # Sort entries by updated date (newest first)
                    entries = sorted(
                        entries,
                        key=lambda x: x.get("updated") or x.get("published") or datetime.min,
                        reverse=True
                    )
                    
                    # Get new entries
                    new_entries = feed_parser.get_new_entries(entries, last_entry_id)
                    
                    if not new_entries:
                        logger.info(f"No new entries in feed: {feed_url}")
                        # Update last_entry_id to the most recent entry even if no new ones
                        if entries:
                            await db.update_feed_metadata(
                                feed_id,
                                datetime.utcnow(),
                                entries[0]["id"]
                            )
                        continue
                    
                    logger.info(f"Found {len(new_entries)} new entry/entries in feed: {feed_url}")
                    
                    # Get all subscriptions for this feed with excluded tags
                    subscriptions = await db.get_subscriptions_with_excluded_tags(feed_id)
                    
                    if not subscriptions:
                        logger.info(f"No subscriptions for feed: {feed_url}")
                        # Still update metadata
                        if entries:
                            await db.update_feed_metadata(
                                feed_id,
                                datetime.utcnow(),
                                entries[0]["id"]
                            )
                        continue
                    
                    # Process each subscription
                    for subscription in subscriptions:
                        subscription_id = subscription["subscription_id"]
                        channel_id = subscription["channel_id"]
                        
                        # Get excluded tag names for this subscription (now using tag_name, not tag_url)
                        excluded_tag_names = set(subscription.get("excluded_tags", []))
                        
                        # Filter entries by excluded tag names (case-insensitive)
                        filtered_entries = feed_parser.filter_entries_by_tags(
                            new_entries,
                            excluded_tag_names
                        )
                        
                        # Send notifications for filtered entries
                        for entry in filtered_entries:
                            entry_id = entry["id"]
                            
                            # Check if already notified
                            if await db.is_entry_notified(subscription_id, entry_id):
                                continue
                            
                            # Send notification
                            success = await self.send_entry_notification(entry, channel_id)
                            
                            if success:
                                # Record notification
                                await db.record_notification(subscription_id, entry_id)
                    
                    # Update feed metadata
                    if entries:
                        await db.update_feed_metadata(
                            feed_id,
                            datetime.utcnow(),
                            entries[0]["id"]
                        )
                    
                    # Small delay between feeds to avoid rate limiting
                    await asyncio.sleep(2)
                
                except Exception as e:
                    logger.error(f"Error processing feed {feed.get('tag_id', 'unknown')}: {e}", exc_info=True)
                    continue
            
            logger.info("Feed polling cycle completed")
        
        except Exception as e:
            logger.error(f"Error in polling cycle: {e}", exc_info=True)
    
    @poll_feeds.before_loop
    async def before_poll_feeds(self):
        """Wait until bot is ready before starting polling."""
        await self.wait_until_ready()
        logger.info("Bot is ready, starting feed polling...")


def main():
    """Main entry point for the bot."""
    bot = AO3TrackerBot()
    
    try:
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()
