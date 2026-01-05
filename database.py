"""Database operations for AO3 Discord RSS Tracker Bot."""
import asyncpg
import logging
from typing import Optional, List, Dict
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)


class Database:
    """Database connection and operations manager."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                min_size=2,
                max_size=10
            )
            logger.info("Database connection pool created")
            await self.init_schema()
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def init_schema(self):
        """Initialize database schema."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Create feeds table (stores tag_id, not full URL)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feeds (
                        id SERIAL PRIMARY KEY,
                        tag_id TEXT UNIQUE NOT NULL,
                        last_updated TIMESTAMP,
                        last_entry_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create feed_channels table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS feed_channels (
                        id SERIAL PRIMARY KEY,
                        feed_id INTEGER REFERENCES feeds(id) ON DELETE CASCADE,
                        channel_id BIGINT NOT NULL,
                        server_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(feed_id, channel_id)
                    )
                """)
                
                # Create server_settings table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS server_settings (
                        id SERIAL PRIMARY KEY,
                        server_id BIGINT UNIQUE NOT NULL,
                        require_permissions BOOLEAN DEFAULT FALSE,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_by BIGINT
                    )
                """)
                
                # Create excluded_tags table (stores tag_name, not tag_url)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS excluded_tags (
                        id SERIAL PRIMARY KEY,
                        feed_channel_id INTEGER REFERENCES feed_channels(id) ON DELETE CASCADE,
                        tag_name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(feed_channel_id, tag_name)
                    )
                """)
                
                # Create notified_entries table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS notified_entries (
                        id SERIAL PRIMARY KEY,
                        feed_channel_id INTEGER REFERENCES feed_channels(id) ON DELETE CASCADE,
                        entry_id TEXT NOT NULL,
                        notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(feed_channel_id, entry_id)
                    )
                """)
                
                # Create indexes for better performance
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_feeds_tag_id ON feeds(tag_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_channels_feed ON feed_channels(feed_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_channels_channel ON feed_channels(channel_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_server_settings_server ON server_settings(server_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_excluded_tags_subscription ON excluded_tags(feed_channel_id)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_notified_entries_subscription ON notified_entries(feed_channel_id)")
                
                logger.info("Database schema initialized")
    
    # Feed operations
    async def get_or_create_feed(self, tag_id: str) -> int:
        """Get feed_id if exists by tag_id, otherwise create and return feed_id."""
        async with self.pool.acquire() as conn:
            # Try to get existing feed
            feed_id = await conn.fetchval(
                "SELECT id FROM feeds WHERE tag_id = $1",
                tag_id
            )
            
            if feed_id:
                return feed_id
            
            # Create new feed
            feed_id = await conn.fetchval(
                "INSERT INTO feeds (tag_id) VALUES ($1) RETURNING id",
                tag_id
            )
            logger.info(f"Created new feed: tag_id={tag_id} (id: {feed_id})")
            return feed_id
    
    async def get_feed_by_tag_id(self, tag_id: str) -> Optional[Dict]:
        """Get feed by tag_id. Returns None if not found."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, tag_id, last_updated, last_entry_id, created_at FROM feeds WHERE tag_id = $1",
                tag_id
            )
            if row:
                return dict(row)
            return None
    
    async def update_feed_metadata(self, feed_id: int, last_updated: datetime, last_entry_id: str):
        """Update feed tracking metadata."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE feeds SET last_updated = $1, last_entry_id = $2 WHERE id = $3",
                last_updated, last_entry_id, feed_id
            )
    
    async def get_all_feeds(self) -> List[Dict]:
        """Get all unique feeds for polling."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, tag_id, last_updated, last_entry_id FROM feeds"
            )
            return [dict(row) for row in rows]
    
    # Feed-Channel subscription operations
    async def create_subscription(self, feed_id: int, channel_id: int, server_id: int) -> int:
        """Create feed-channel subscription. Returns subscription id."""
        async with self.pool.acquire() as conn:
            try:
                subscription_id = await conn.fetchval(
                    "INSERT INTO feed_channels (feed_id, channel_id, server_id) VALUES ($1, $2, $3) RETURNING id",
                    feed_id, channel_id, server_id
                )
                logger.info(f"Created subscription: feed_id={feed_id}, channel_id={channel_id}")
                return subscription_id
            except asyncpg.UniqueViolationError:
                # Subscription already exists
                subscription_id = await conn.fetchval(
                    "SELECT id FROM feed_channels WHERE feed_id = $1 AND channel_id = $2",
                    feed_id, channel_id
                )
                return subscription_id
    
    async def delete_subscription(self, feed_id: int, channel_id: int) -> bool:
        """Delete feed-channel subscription. Returns True if deleted."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM feed_channels WHERE feed_id = $1 AND channel_id = $2",
                feed_id, channel_id
            )
            deleted = result.split()[-1] == "1"
            if deleted:
                logger.info(f"Deleted subscription: feed_id={feed_id}, channel_id={channel_id}")
            return deleted
    
    async def get_subscriptions_by_feed(self, feed_id: int) -> List[Dict]:
        """Get all channels subscribed to a feed."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, feed_id, channel_id, server_id, created_at
                FROM feed_channels
                WHERE feed_id = $1
                """,
                feed_id
            )
            return [dict(row) for row in rows]
    
    async def get_subscriptions_by_channel(self, channel_id: int) -> List[Dict]:
        """Get all feeds subscribed by a channel."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT fc.id, fc.feed_id, fc.channel_id, fc.server_id, fc.created_at,
                       f.tag_id, f.last_updated, f.last_entry_id
                FROM feed_channels fc
                JOIN feeds f ON fc.feed_id = f.id
                WHERE fc.channel_id = $1
                ORDER BY fc.created_at DESC
                """,
                channel_id
            )
            return [dict(row) for row in rows]
    
    async def subscription_exists(self, feed_id: int, channel_id: int) -> bool:
        """Check if subscription already exists."""
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM feed_channels WHERE feed_id = $1 AND channel_id = $2)",
                feed_id, channel_id
            )
            return exists
    
    async def get_subscription_by_id(self, subscription_id: int) -> Optional[Dict]:
        """Get subscription by id."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT fc.id, fc.feed_id, fc.channel_id, fc.server_id, fc.created_at,
                       f.tag_id
                FROM feed_channels fc
                JOIN feeds f ON fc.feed_id = f.id
                WHERE fc.id = $1
                """,
                subscription_id
            )
            if row:
                return dict(row)
            return None
    
    # Server settings operations
    async def get_require_permissions(self, server_id: int) -> bool:
        """Get whether server requires permissions (default: False)."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT require_permissions FROM server_settings WHERE server_id = $1",
                server_id
            )
            return result if result is not None else False
    
    async def set_require_permissions(self, server_id: int, require: bool, updated_by: int):
        """Set permission requirement for a server."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO server_settings (server_id, require_permissions, updated_by, updated_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT (server_id) 
                DO UPDATE SET 
                    require_permissions = $2,
                    updated_by = $3,
                    updated_at = CURRENT_TIMESTAMP
            """, server_id, require, updated_by)
            logger.info(f"Updated require_permissions for server {server_id}: {require}")
    
    async def get_server_setting(self, server_id: int, setting_name: str) -> Optional[any]:
        """Get server setting value."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT {setting_name} FROM server_settings WHERE server_id = $1",
                server_id
            )
            return result
    
    async def get_server_settings(self, server_id: int) -> Optional[Dict]:
        """Get all server settings."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT server_id, require_permissions, updated_at, updated_by FROM server_settings WHERE server_id = $1",
                server_id
            )
            if row:
                return dict(row)
            return None
    
    # Excluded tags operations (now using tag_name instead of tag_url)
    async def add_excluded_tag(self, feed_channel_id: int, tag_name: str) -> bool:
        """Add tag name to exclusion list. Returns True if added."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO excluded_tags (feed_channel_id, tag_name) VALUES ($1, $2)",
                    feed_channel_id, tag_name
                )
                logger.info(f"Added excluded tag: feed_channel_id={feed_channel_id}, tag_name={tag_name}")
                return True
            except asyncpg.UniqueViolationError:
                # Tag already excluded
                return False
    
    async def remove_excluded_tag(self, feed_channel_id: int, tag_name: str) -> bool:
        """Remove tag name from exclusion list. Returns True if removed."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM excluded_tags WHERE feed_channel_id = $1 AND tag_name = $2",
                feed_channel_id, tag_name
            )
            deleted = result.split()[-1] == "1"
            if deleted:
                logger.info(f"Removed excluded tag: feed_channel_id={feed_channel_id}, tag_name={tag_name}")
            return deleted
    
    async def get_excluded_tags(self, feed_channel_id: int) -> List[str]:
        """Get excluded tag names for a subscription."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT tag_name FROM excluded_tags WHERE feed_channel_id = $1",
                feed_channel_id
            )
            return [row["tag_name"] for row in rows]
    
    async def get_subscriptions_with_excluded_tags(self, feed_id: int) -> List[Dict]:
        """Get all subscriptions for a feed with their excluded tags."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT fc.id as subscription_id, fc.channel_id, fc.server_id,
                       COALESCE(
                           json_agg(et.tag_name) FILTER (WHERE et.tag_name IS NOT NULL),
                           '[]'::json
                       ) as excluded_tags
                FROM feed_channels fc
                LEFT JOIN excluded_tags et ON fc.id = et.feed_channel_id
                WHERE fc.feed_id = $1
                GROUP BY fc.id, fc.channel_id, fc.server_id
                """,
                feed_id
            )
            return [dict(row) for row in rows]
    
    # Notified entries operations
    async def is_entry_notified(self, feed_channel_id: int, entry_id: str) -> bool:
        """Check if entry has been notified for this subscription."""
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM notified_entries WHERE feed_channel_id = $1 AND entry_id = $2)",
                feed_channel_id, entry_id
            )
            return exists
    
    async def record_notification(self, feed_channel_id: int, entry_id: str):
        """Record that an entry has been notified."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO notified_entries (feed_channel_id, entry_id) VALUES ($1, $2)",
                    feed_channel_id, entry_id
                )
            except asyncpg.UniqueViolationError:
                # Already recorded, ignore
                pass


# Global database instance
db = Database()
