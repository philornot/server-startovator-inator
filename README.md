# Minecraft Server Discord Bot

A Discord bot for managing your Minecraft server remotely with full internationalization support.

## Features

- **Start/Stop/Kill** - Control your Minecraft server remotely
- **Status monitoring** - Real-time server status updates via Discord presence
- **Logging** - Timestamped logs with server output capture
- **Background operation** - Run as Windows service or scheduled task
- **Configurable** - All settings in one JSON file
- **Multi-language** - English and Polish translations included

## Requirements

- Python 3.10 or higher
- Discord.py 2.0 or higher
- A Discord bot token
- Windows (for .bat server scripts)

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Configuration
```bash
# Copy example config
copy config.example.json config.json

# Create .env file for token
echo DISCORD_TOKEN=your_token_here > .env
```

### 3. Edit Configuration

Open `config.json` and configure:
- `server.directory` - Path to your Minecraft server folder (use `\\` for Windows paths)
- `server.start_script` - Name of your startup script (e.g., `start-server.bat`)
- `language` - Choose `"en"` or `"pl"`

### 4. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application
3. Navigate to Bot section and click Add Bot
4. Copy the token and paste it into your `.env` file
5. Enable **Message Content Intent** in Bot settings
6. Go to OAuth2 URL Generator:
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: `Send Messages`, `Use Slash Commands`
   - Copy the generated URL and invite the bot to your server

### 5. Run the Bot

**For testing:**
```bash
python bot.py
```

**For production (run in background):**

See the next section for setting up automatic startup.

## Running as Background Service

You have two options for running the bot automatically on Windows startup.

### Option A: Task Scheduler (Recommended)

Run the included setup script as Administrator:

```bash
python setup_autostart.py
```

This will configure Windows Task Scheduler to start the bot on system startup.

To manage the task:
```bash
# Start the bot manually
schtasks /run /tn MinecraftBot

# Stop the bot
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq bot.py*"

# Remove autostart
schtasks /delete /tn MinecraftBot /f
```

### Option B: NSSM (Advanced)

For more control, you can use NSSM (Non-Sucking Service Manager):

1. Download NSSM from the official site: https://nssm.cc/download
2. Extract `nssm.exe` from the appropriate folder (`win64` for 64-bit systems)
3. Open Command Prompt as Administrator
4. Run:

```bash
nssm.exe install MinecraftBot
```

5. In the NSSM GUI:
   - Application Path: Path to `python.exe` (e.g., `C:\Python311\python.exe`)
   - Startup directory: Path to bot folder
   - Arguments: `bot.py`

6. Start the service:
```bash
nssm.exe start MinecraftBot
```

**Managing the service:**
```bash
# Start the service
nssm.exe start MinecraftBot

# Stop the service
nssm.exe stop MinecraftBot

# Restart the service
nssm.exe restart MinecraftBot

# Check service status
nssm.exe status MinecraftBot

# Remove the service
nssm.exe remove MinecraftBot confirm
```

You can also manage the service through Windows Services GUI (`services.msc`).

NSSM provides additional features like automatic restart on crash and detailed logging.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the Minecraft server |
| `/stop` | Stop the server gracefully |
| `/kill` | Force kill the server process |
| `/status` | Show current server status and recent logs |
| `/logs` | Show last 30 lines from server.log |
| `/config` | Display current bot configuration |

## Configuration

### Server Settings
```json
{
  "server": {
    "directory": "C:\\path\\to\\minecraft\\server",
    "start_script": "start-server.bat",
    "stop_timeout": 60
  }
}
```

- `directory` - Full path to Minecraft server folder
- `start_script` - Startup script filename
- `stop_timeout` - Seconds to wait for graceful shutdown (default: 60)

### Logging Settings
```json
{
  "logging": {
    "bot_log_file": "bot.log",
    "status_log_lines": 15
  }
}
```

- `bot_log_file` - Log file path (default: "bot.log")
- `status_log_lines` - Number of log lines shown in `/status` (default: 15)

### Language
```json
{
  "language": "en"
}
```

Set to `"pl"` for Polish or `"en"` for English.

## Adding New Languages

Edit `config.json` and add a new translation section:

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

Then set `"language": "de"` in your configuration.

## Updating the bot

After updating the code (e.g., via git pull), restart the bot:

**If using Task Scheduler:**
```bash
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq bot.py*"
schtasks /run /tn MinecraftBot
```

**If using NSSM:**
```bash
nssm.exe restart MinecraftBot
```

## Log Files

- `bot.log` - Bot activity and server output
- `server/server.log` - Minecraft server log

## Security notes

- Never commit your `.env` file or actual `config.json` to version control
- Keep your Discord token private
- The bot requires access to start/stop the server process
- Ensure only trusted users have access to bot commands on Discord

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Polish README:** [README-PL.md](README-PL.md)