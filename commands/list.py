"""List command for viewing tracked feeds."""
import discord
from discord import app_commands
from discord.ext import commands
import logging
from database import db

logger = logging.getLogger(__name__)


class ListCommand(commands.Cog):
    """List command for viewing subscriptions."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="list", description="List all feed subscriptions for a channel")
    @app_commands.describe(
        channel="The channel to list subscriptions for (defaults to current channel)"
    )
    async def list_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """Slash command to list subscriptions."""
        # Defer response immediately to avoid interaction timeout
        await interaction.response.defer(ephemeral=True)
        
        target_channel = channel or interaction.channel
        
        try:
            subscriptions = await db.get_subscriptions_by_channel(target_channel.id)
            
            if not subscriptions:
                await interaction.followup.send(
                    f"📭 No subscriptions found for {target_channel.mention}.",
                    ephemeral=True
                )
                return
            
            # Build embed
            embed = discord.Embed(
                title=f"Subscriptions for {target_channel.name}",
                color=discord.Color.blue()
            )
            
            for sub in subscriptions[:25]:  # Discord limit is 25 fields
                tag_id = sub["tag_id"]
                subscription_id = sub["id"]
                created_at = sub["created_at"].strftime("%Y-%m-%d") if sub["created_at"] else "Unknown"
                
                # Get excluded tags count
                excluded_tags = await db.get_excluded_tags(subscription_id)
                excluded_count = len(excluded_tags)
                
                embed.add_field(
                    name=f"ID: {subscription_id}",
                    value=(
                        f"**Tag ID:** {tag_id}\n"
                        f"**Feed URL:** [Link](https://archiveofourown.org/tags/{tag_id}/feed.atom)\n"
                        f"**Excluded Tags:** {excluded_count}\n"
                        f"**Created:** {created_at}"
                    ),
                    inline=False
                )
            
            if len(subscriptions) > 25:
                embed.set_footer(text=f"Showing 25 of {len(subscriptions)} subscriptions")
            
            await interaction.followup.send(embed=embed, ephemeral=False)
        
        except Exception as e:
            logger.error(f"Error in list command: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred while listing subscriptions: {str(e)}",
                ephemeral=True
            )
    
    @commands.command(name="list")
    async def list_prefix(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Prefix command to list subscriptions."""
        target_channel = channel or ctx.channel
        
        try:
            subscriptions = await db.get_subscriptions_by_channel(target_channel.id)
            
            if not subscriptions:
                await ctx.send(f"📭 No subscriptions found for {target_channel.mention}.")
                return
            
            # Build message
            message_parts = [f"**Subscriptions for {target_channel.mention}:**\n"]
            
            for sub in subscriptions[:20]:  # Limit to avoid message length issues
                tag_id = sub["tag_id"]
                subscription_id = sub["id"]
                created_at = sub["created_at"].strftime("%Y-%m-%d") if sub["created_at"] else "Unknown"
                
                excluded_tags = await db.get_excluded_tags(subscription_id)
                excluded_count = len(excluded_tags)
                
                message_parts.append(
                    f"**ID {subscription_id}:** Tag ID `{tag_id}`\n"
                    f"  Feed: https://archiveofourown.org/tags/{tag_id}/feed.atom\n"
                    f"  Excluded Tags: {excluded_count} | Created: {created_at}\n"
                )
            
            if len(subscriptions) > 20:
                message_parts.append(f"\n*Showing 20 of {len(subscriptions)} subscriptions*")
            
            await ctx.send("".join(message_parts))
        
        except Exception as e:
            logger.error(f"Error in list command: {e}", exc_info=True)
            await ctx.send(f"❌ An error occurred while listing subscriptions: {str(e)}")


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(ListCommand(bot))
