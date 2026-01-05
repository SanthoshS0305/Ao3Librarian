# AO3 Discord RSS Tracker Bot

Tracks Archive of Our Own (AO3) RSS feeds and sends notifications when new works are published.

## Quick Start

**[Invite Bot to Server](https://discord.com/oauth2/authorize?client_id=1457586647393894511&permissions=2147567616&integration_type=0&scope=bot+applications.commands)**

### Usage

1. Track a feed: `/track 541570` (use any AO3 tag ID)
2. List subscriptions: `/list`
3. Exclude tags: `/exclude <subscription_id> <tag_url>`
4. View status: `/status <tag_id>`

Find tag IDs from AO3 tag URLs: `https://archiveofourown.org/tags/541570` → tag ID is `541570`

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

Prefix commands also available: `!track 541570`, etc.

## Features

- Efficient: Each feed fetched once, shared across all channels
- Flexible: Per-channel tag exclusions
- Optional permissions: Open by default, admins can restrict
- Rich notifications: Embeds with work details

## Self-Hosting

### Prerequisites

- Python 3.8+ or Docker
- PostgreSQL database
- Discord Bot Token from [Discord Developer Portal](https://discord.com/developers/applications)

### Docker Setup

```bash
git clone <repository-url>
cd ao3UpdateTracker
cp .env.example .env
# Edit .env and add DISCORD_TOKEN

docker-compose up -d
docker-compose logs -f bot
```

### Manual Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
createdb ao3_tracker

cp .env.example .env
# Edit .env with DISCORD_TOKEN and database credentials

python bot.py
```

### Discord Bot Setup

1. [Discord Developer Portal](https://discord.com/developers/applications) → Create application
2. Bot section → Create bot → Copy token
3. Enable **MESSAGE CONTENT INTENT**
4. OAuth2 → URL Generator: scopes `bot`, `applications.commands`, permissions: Send Messages, Embed Links, Read Message History
5. Add token to `.env`: `DISCORD_TOKEN=your_token_here`

### Environment Variables

**Required:**
- `DISCORD_TOKEN` - Discord bot token
- `DB_PASSWORD` - PostgreSQL password

**Optional (defaults):**
- `DB_HOST=localhost`, `DB_PORT=5432`, `DB_NAME=ao3_tracker`, `DB_USER=postgres`
- `COMMAND_PREFIX=!`, `POLLING_INTERVAL=3600`

## Troubleshooting

**Bot offline:** Check logs: `docker-compose logs bot` or terminal output

**Commands not working:** Enable MESSAGE CONTENT INTENT for prefix commands

**Database errors:** Verify PostgreSQL is running and credentials are correct

**Feeds not updating:** Check bot logs, verify feed URLs are accessible
