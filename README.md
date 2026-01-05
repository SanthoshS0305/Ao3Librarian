# AO3 Discord RSS Tracker Bot

A Discord bot that tracks Archive of Our Own (AO3) RSS feeds and sends notifications when new works are published.

## Quick Start (Users)

### Invite the Bot

**[Invite Bot to Your Server](https://discord.com/oauth2/authorize?client_id=1457586647393894511&permissions=2147567616&integration_type=0&scope=bot+applications.commands)**

### Basic Usage

1. **Track a feed**: `/track 541570` (use any AO3 tag ID)
2. **List subscriptions**: `/list`
3. **Exclude tags**: `/exclude <subscription_id> <tag_url>`
4. **View status**: `/status <tag_id>`

**Example:** To track works tagged with "Katie Bell/Harry Potter":
- Find the tag ID from the AO3 tag URL (e.g., `https://archiveofourown.org/tags/541570` → tag ID is `541570`)
- Run `/track 541570` in your Discord channel

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/track <tag_id> [channel]` | Subscribe channel to a feed | `/track 541570` |
| `/untrack <tag_id>` | Unsubscribe from a feed | `/untrack 541570` |
| `/exclude <subscription_id> <tag_url>` | Exclude works with a tag | `/exclude 1 https://archiveofourown.org/tags/SomeTag` |
| `/unexclude <subscription_id> <tag_url>` | Remove tag exclusion | `/unexclude 1 https://archiveofourown.org/tags/SomeTag` |
| `/list [channel]` | List all subscriptions | `/list` |
| `/status <tag_id>` | Show feed status | `/status 541570` |
| `/settings` | View server settings | `/settings` |
| `/settings require_permissions <true/false>` | Enable/disable permission checks | `/settings require_permissions true` |

All commands also work with prefix `!` (e.g., `!track 541570`).

## Features

- **Efficient**: Each feed fetched once, shared across all channels
- **Flexible**: Per-channel tag exclusions
- **Optional Permissions**: Anyone can use by default; admins can restrict
- **Rich Notifications**: Beautiful embeds with work details

## Self-Hosting (Developers)

### Prerequisites

- Python 3.8+ or Docker
- PostgreSQL database
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))

### Quick Setup with Docker

```bash
# 1. Clone and configure
git clone <repository-url>
cd ao3UpdateTracker
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN

# 2. Start
docker-compose up -d

# 3. View logs
docker-compose logs -f bot
```

### Manual Setup

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Set up database
createdb ao3_tracker

# 3. Configure
cp .env.example .env
# Edit .env with your DISCORD_TOKEN and database credentials

# 4. Run
python bot.py
```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create application → Bot section → Create bot
3. Copy token → Enable **MESSAGE CONTENT INTENT**
4. OAuth2 → URL Generator:
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Embed Links, Read Message History
5. Add token to `.env`: `DISCORD_TOKEN=your_token_here`

### Environment Variables

Required:
- `DISCORD_TOKEN` - Your Discord bot token
- `DB_PASSWORD` - PostgreSQL password

Optional (defaults shown):
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `DB_NAME=ao3_tracker`
- `DB_USER=postgres`
- `COMMAND_PREFIX=!`
- `POLLING_INTERVAL=3600` (1 hour)

## How It Works

- Stores only tag IDs (e.g., `541570`) instead of full URLs
- Constructs feed URLs: `https://archiveofourown.org/tags/{tag_id}/feed.atom`
- Fetches each unique feed once per polling cycle
- Distributes updates to all subscribed channels
- Filters by tag names (case-insensitive)

## Troubleshooting

**Bot offline?** Check logs: `docker-compose logs bot` or check terminal output

**Commands not working?** Ensure MESSAGE CONTENT INTENT is enabled (for prefix commands)

**Database errors?** Verify PostgreSQL is running and credentials are correct

**Feeds not updating?** Check bot logs for errors, verify feed URLs are accessible

## License

[Add your license here]
