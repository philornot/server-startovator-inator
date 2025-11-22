# Minecraft Server Discord Bot

A Discord bot for managing your Minecraft server remotely with full internationalization support.

## Features

- **Start/Stop/Kill** - Control your Minecraft server remotely
- **Status monitoring** - Real-time server status updates
- **Logging** - Timestamped logs with server output capture
- **Configurable** - All settings in one JSON file

## Requirements

- Python 3.10+
- Discord.py 2.0+
- A Discord bot token
- Windows (for .bat server scripts)

## Installation

1. **Clone or download** this repository

2. **Install dependencies:**
   ```bash
   pip install discord.py python-dotenv
   ```

3. **Create configuration file:**
   ```bash
   cp config.example.json config.json
   ```

4. **Edit `config.json`** and fill in your settings:
   - `discord_token` - Your Discord bot token (or use `.env` file)
   - `server.directory` - Path to your Minecraft server folder
   - `server.start_script` - Name of your startup script (e.g., `start-server.bat`)
   - `language` - Choose `"en"` or `"pl"`

5. **Create Discord bot:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create New Application
   - Go to Bot section → Add Bot
   - Copy token and paste into `config.json` OR create `.env` file:
     ```
     DISCORD_TOKEN=your_token_here
     ```
   - Enable **Message Content Intent** in Bot settings
   - Go to OAuth2 → URL Generator:
     - Select scopes: `bot`, `applications.commands`
     - Select permissions: `Send Messages`, `Use Slash Commands`
     - Copy generated URL and invite bot to your server

6. **Run the bot:**
   ```bash
   python bot.py
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the Minecraft server |
| `/stop` | Stop the server gracefully (sends "stop" command) |
| `/kill` | Force kill the server process |
| `/status` | Show current server status and recent logs |
| `/config` | Display current bot configuration |

## Configuration Options

### Server Settings
- `directory` - Full path to Minecraft server folder
- `start_script` - Startup script filename
- `stop_timeout` - Seconds to wait for graceful shutdown (default: 60)

### Logging Settings
- `bot_log_file` - Log file path (default: "bot.log")
- `status_log_lines` - Number of log lines shown in `/status` (default: 15)

### Language
Set `"language": "pl"` for Polish or `"language": "en"` for English

## Adding New Languages

Edit `config.json` and add a new translation section under `translations`:

```json
"translations": {
  "en": { ... },
  "pl": { ... },
  "de": {
    "already_running": "Server läuft bereits.",
    "starting": "Server wird gestartet...",
    ...
  }
}
```

Then set `"language": "de"` to use it.

## Troubleshooting

### Bot doesn't respond to commands
- Check if bot has proper permissions in Discord server
- Verify **Message Content Intent** is enabled in Discord Developer Portal
- Run `/config` command to verify settings are loaded correctly

### "config.json not found" error
- Copy `config.example.json` to `config.json`
- Edit the file with your settings

### Server won't start
- Verify `server.directory` path is correct (use double backslashes `\\` on Windows)
- Check if `start_script` exists in the server directory
- Review `bot.log` for detailed error messages

### Status shows "Error" after stop
- Normal if server crashed or was killed
- Check last exit code in `/status` command
- Review server logs for crash details

## License

MIT License - Feel free to modify and distribute

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

**Polish README available as:** [README-PL.md](README-PL.md)