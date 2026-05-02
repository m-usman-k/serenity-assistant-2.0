# Serenity Assistant 2.0

Serenity Assistant is a comprehensive Discord bot written in Python using discord.py. It is designed to handle advanced moderation, leveling, economy, logging, and welcome messaging, storing all relevant data locally in a SQLite database.

## Features

- Moderation: Timeout, kick, ban, warnings, and automod for banned words.
- Leveling: XP system that rewards users for messaging, complete with ranks and a leaderboard.
- Economy: Wallet system with daily work commands and user-to-user payments.
- Logging: Extensive tracking of server events including message edits/deletions, member changes, and channel updates. All logs are stored in the database for potential web dashboard integration.
- Welcome & Goodbye: Automatically generates custom welcome and goodbye image cards using easy-pil.
- Utility: Sticky messages, AFK status tracking, and reaction role setup.

## Setup

1. Install the dependencies:
   pip install -r requirements.txt

2. Create a .env file in the root directory and add your bot token:
   BOT_TOKEN=your_bot_token_here

3. Run the bot:
   python main.py

The database (database.sqlite) will be created automatically on the first run.
