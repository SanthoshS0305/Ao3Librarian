#!/bin/bash
# Setup script for AO3 Discord RSS Tracker Bot

set -e

echo "=== AO3 Discord RSS Tracker Bot Setup ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "✅ Python $(python3 --version) found"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo ""
    echo "⚠️  PostgreSQL not found. Installing..."
    echo "Run: sudo pacman -S postgresql"
    echo "Then: sudo systemctl start postgresql"
    echo "Then: sudo systemctl enable postgresql"
    echo ""
    read -p "Press Enter after installing PostgreSQL, or Ctrl+C to exit..."
fi

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql 2>/dev/null; then
    echo "⚠️  PostgreSQL service not running. Starting..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi
echo "✅ PostgreSQL service is running"

# Create database
echo ""
echo "Creating database..."
sudo -u postgres createdb ao3_tracker 2>/dev/null && echo "✅ Database created" || echo "⚠️  Database may already exist (this is OK)"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv --system-site-packages
echo "✅ Virtual environment created"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
venv/bin/python -m pip install --upgrade pip --quiet
venv/bin/python -m pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Check .env file
echo ""
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env file created. Please edit it and add your DISCORD_TOKEN and DB_PASSWORD"
    else
        echo "❌ .env.example not found. Please create .env manually."
    fi
else
    echo "✅ .env file exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your DISCORD_TOKEN and DB_PASSWORD"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run the bot: python bot.py"
echo ""
