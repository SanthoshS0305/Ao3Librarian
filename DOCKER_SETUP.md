# Docker Setup Guide

## Install Docker

On Manjaro/Arch:
```bash
sudo pacman -S docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**Important:** Log out and back in (or run `newgrp docker`) for group changes to take effect.

## Run the Bot

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop
docker-compose down
```

The bot will automatically:
- Set up PostgreSQL in a container
- Create database tables
- Start the bot

## Verify .env File

Make sure your `.env` has:
- `DISCORD_TOKEN` - Your bot token
- `DB_PASSWORD` - PostgreSQL password (used by both containers)
