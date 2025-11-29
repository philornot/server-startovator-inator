import asyncio
import json
import os
import subprocess
import threading
import traceback
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Import AI module (optional - bot works without it)
try:
    from ai import AIBot, load_ai_config

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("[WARN] ai.py not found - AI responses disabled")

load_dotenv()

# ===============================
#   Configuration
# ===============================
CONFIG_FILE = "config.json"
AI_CONFIG_FILE = "ai-config.json"


def load_config():
    """Load configuration from config.json"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERROR] Configuration file '{CONFIG_FILE}' not found!")
        print("Please create config.json based on config.example.json")
        exit(1)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in config.json: {e}")
        exit(1)


config = load_config()

# Load settings
TOKEN = os.getenv("DISCORD_TOKEN") or config.get("discord_token")
if not TOKEN:
    print("[ERROR] Discord token not found! Set DISCORD_TOKEN in .env or config.json")
    exit(1)

SERVER_DIR = config["server"]["directory"]
START_BAT = os.path.join(SERVER_DIR, config["server"]["start_script"])
LOG_FILE = config["logging"]["bot_log_file"]

# Verify paths
if not os.path.exists(SERVER_DIR):
    print(f"[ERROR] Server directory not found: {SERVER_DIR}")
    exit(1)

if not os.path.exists(START_BAT):
    print(f"[ERROR] Start script not found: {START_BAT}")
    exit(1)

# Load language
LANG = config.get("language", "en")
TRANSLATIONS = config["translations"][LANG]

# Initialize AI (if available)
ai_bot = None
ai_config = {}
if AI_AVAILABLE:
    try:
        ai_config = load_ai_config(AI_CONFIG_FILE)
        if ai_config.get("enabled", False):
            ai_bot = AIBot(config, ai_config, TRANSLATIONS)
            if ai_bot.enabled:
                print("[INFO] AI personality module loaded successfully")
                # Load saved personality if available
                saved_personality = ai_config.get("current_personality")
                if saved_personality and saved_personality != ai_bot.personality_key:
                    if ai_bot.load_personality(saved_personality):
                        print(f"[INFO] Restored saved personality: {saved_personality}")
        else:
            print("[INFO] AI module disabled in config")
    except Exception as e:
        print(f"[WARN] Failed to initialize AI module: {e}")
        ai_bot = None

# Global state
server_process: Optional[subprocess.Popen] = None
server_in_error = False
last_exit_code = None
last_status = None


# ===============================
#   Logging
# ===============================
def get_timestamp() -> str:
    """Get formatted timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str, level: str = "INFO"):
    """Write log message with timestamp"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{get_timestamp()}] [{level}] {msg}\n")
        print(f"[{get_timestamp()}] [{level}] {msg}")
    except Exception as e:
        print(f"[{get_timestamp()}] [ERROR] Failed to write log: {e}")


def log_exception(msg: str):
    """Write error log with timestamp and traceback"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{get_timestamp()}] [ERROR] {msg}\n")
            f.write(traceback.format_exc() + "\n")
        print(f"[{get_timestamp()}] [ERROR] {msg}")
        print(traceback.format_exc())
    except Exception as e:
        print(f"[{get_timestamp()}] [ERROR] Failed to write error log: {e}")


def read_last_log_lines(n: int = 20) -> str:
    """Read last N lines from log file"""
    if not os.path.exists(LOG_FILE):
        return TRANSLATIONS["no_logs"]
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-n:]) if lines else TRANSLATIONS["no_logs"]
    except Exception as e:
        log_exception(f"Failed to read log file: {e}")
        return f"(error reading logs: {e})"


# ===============================
#   Process management utilities
# ===============================
def kill_process_tree(pid: int):
    """Kill process and all its children (Windows-specific)"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
            timeout=10
        )
        log(f"Killed process tree for PID {pid}", "INFO")
    except subprocess.TimeoutExpired:
        log(f"Taskkill timeout for PID {pid}", "WARN")
    except Exception as e:
        log_exception(f"Failed to kill process tree: {e}")


# ===============================
#   Process monitoring
# ===============================
def monitor_process():
    """Monitor server process and log when it exits"""
    global server_process, server_in_error, last_exit_code

    if server_process is None:
        return

    try:
        for line in server_process.stdout:
            stripped = line.strip()
            if stripped:
                log(f"{stripped}", "SERVER")

        exit_code = server_process.wait()
        last_exit_code = exit_code

        if exit_code != 0:
            server_in_error = True
            log(f"Server process exited with code {exit_code}", "ERROR")
        else:
            log("Server process exited normally", "INFO")

    except Exception as e:
        log_exception(f"monitor_process crashed: {e}")
        server_in_error = True


# ===============================
#   Bot class
# ===============================
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Called when bot is ready - sync commands and start status loop"""
        try:
            await self.tree.sync()
            log("Bot ready. Commands synced.", "INFO")

            await self.update_initial_status()
            update_status.start()
        except Exception as e:
            log_exception(f"Error in setup_hook: {e}")

    async def update_initial_status(self):
        """Set correct initial status when bot starts"""
        global server_in_error

        try:
            if server_in_error:
                await set_status("Error")
            elif server_running():
                await set_status("Online")
            else:
                await set_status("Offline")
            log("Initial status set", "INFO")
        except Exception as e:
            log_exception(f"Failed to set initial status: {e}")


bot = Bot()


# ===============================
#   AI Message Handler
# ===============================
@bot.event
async def on_message(message: discord.Message):
    """Handle messages that mention the bot"""
    # Ignore own messages
    if message.author == bot.user:
        return

    # Process commands normally
    await bot.process_commands(message)

    # Check if bot was mentioned and AI is available
    if bot.user in message.mentions and ai_bot and ai_bot.enabled:
        log(f"Bot mentioned by {message.author.name}: {message.content}", "INFO")

        # Get message history for context
        history = []
        try:
            async for msg in message.channel.history(limit=20):
                history.insert(0, msg)
        except Exception as e:
            log(f"Failed to fetch message history: {e}", "WARN")

        # Generate AI response
        async with message.channel.typing():
            response = await ai_bot.generate_response(
                message, history,
                server_running(), server_in_error, last_exit_code,
                server_process, SERVER_DIR
            )

        # Send response (split if too long)
        if len(response) > 2000:
            chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)


# ===============================
#   Helpers
# ===============================
async def set_status(text: str):
    """Set bot Discord status with appropriate presence"""
    global last_status

    if text == last_status:
        return

    try:
        if not bot.is_ready() or bot.ws is None:
            log("Bot not ready, cannot set status", "DEBUG")
            return

        # Add AI personality name to status if enabled
        personality_info = ""
        if ai_bot and ai_bot.enabled and ai_bot.current_personality:
            personality_name = ai_bot.current_personality.get("name", "")
            personality_info = f" | {personality_name}"

        status_map = {
            "Online": (discord.Status.online, TRANSLATIONS.get("status_online", "🟢 Server Online") + personality_info),
            "Offline": (discord.Status.dnd, TRANSLATIONS.get("status_offline", "⚫ Server Offline") + personality_info),
            "Starting...": (discord.Status.idle,
                            TRANSLATIONS.get("status_starting", "⏳ Starting...") + personality_info),
            "Stopping...": (discord.Status.idle,
                            TRANSLATIONS.get("status_stopping", "⏳ Stopping...") + personality_info),
            "Error": (discord.Status.dnd, TRANSLATIONS.get("status_error", "🔴 Server Error") + personality_info),
        }

        discord_status, activity_text = status_map.get(text, (discord.Status.online, text + personality_info))

        await bot.change_presence(
            status=discord_status,
            activity=discord.Game(name=activity_text)
        )
        log(f"Status: {discord_status.name} - {activity_text}", "STATUS")
        last_status = text
    except Exception as e:
        log_exception(f"Failed to set status to: {text}")


def server_running() -> bool:
    """Check if server process is running"""
    if server_process is None:
        return False
    poll = server_process.poll()
    return poll is None


# ===============================
#   /start
# ===============================
@bot.tree.command(
    name="start",
    description=TRANSLATIONS["cmd_start_desc"]
)
async def start_server(interaction: discord.Interaction):
    global server_process, server_in_error, last_exit_code

    if server_running():
        return await interaction.response.send_message(TRANSLATIONS["already_running"])

    await interaction.response.send_message(TRANSLATIONS["starting"])
    await set_status("Starting...")
    log("=== START COMMAND CALLED ===", "INFO")

    server_in_error = False
    last_exit_code = None

    try:
        log(f"Executing: {START_BAT}", "DEBUG")
        log(f"Working dir: {SERVER_DIR}", "DEBUG")

        server_process = subprocess.Popen(
            START_BAT,
            cwd=SERVER_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            shell=False
        )

        log(f"Process started with PID {server_process.pid}", "INFO")

        monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        monitor_thread.start()
        log("Monitor thread started", "DEBUG")

        await asyncio.sleep(3)

        if not server_running():
            exit_code = server_process.returncode
            server_in_error = True
            last_exit_code = exit_code
            log(f"Process died immediately with code {exit_code}", "ERROR")

            server_log = os.path.join(SERVER_DIR, "server.log")
            error_detail = ""
            if os.path.exists(server_log):
                try:
                    with open(server_log, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        error_detail = "\n" + "".join(lines[-10:])
                except Exception as e:
                    log(f"Failed to read server.log: {e}", "WARN")

            await set_status("Error")
            return await interaction.followup.send(
                f"{TRANSLATIONS['start_error']}\n"
                f"Exit code: {exit_code}\n"
                f"Check `bot.log` and `server/server.log` for details.{error_detail}"
            )

        log("Server process confirmed running", "INFO")
        await set_status("Online")
        await interaction.followup.send(TRANSLATIONS.get("started", "✅ Server started successfully!"))

    except FileNotFoundError:
        server_in_error = True
        log_exception(f"Start script not found: {START_BAT}")
        await set_status("Error")
        return await interaction.followup.send(
            f"{TRANSLATIONS.get('start_script_not_found', 'Start script not found')}: `{START_BAT}`"
        )
    except Exception as e:
        server_in_error = True
        log_exception(f"Failed to start server: {e}")
        await set_status("Error")
        return await interaction.followup.send(
            f"{TRANSLATIONS['start_error']}\n```{str(e)}```"
        )


# ===============================
#   /stop
# ===============================
@bot.tree.command(
    name="stop",
    description=TRANSLATIONS["cmd_stop_desc"]
)
async def stop_server(interaction: discord.Interaction):
    global server_process, server_in_error, last_exit_code

    if not server_running():
        return await interaction.response.send_message(TRANSLATIONS["not_running"])

    await interaction.response.send_message(TRANSLATIONS["stopping"])
    await set_status("Stopping...")
    log("=== STOP COMMAND CALLED ===", "INFO")

    try:
        server_process.stdin.write("stop\n")
        server_process.stdin.flush()
        log("Stop command sent to server", "INFO")
    except Exception as e:
        server_in_error = True
        log_exception(f"Failed to send stop command: {e}")
        await set_status("Error")
        return await interaction.followup.send(TRANSLATIONS["stop_send_error"])

    loop = asyncio.get_event_loop()
    try:
        exit_code = await asyncio.wait_for(
            loop.run_in_executor(None, server_process.wait),
            timeout=config["server"]["stop_timeout"]
        )
        last_exit_code = exit_code
        log(f"Server exited with code: {exit_code}", "INFO")
    except asyncio.TimeoutError:
        server_in_error = True
        log(f"Server didn't stop within {config['server']['stop_timeout']}s timeout", "ERROR")
        await set_status("Error")
        return await interaction.followup.send(
            TRANSLATIONS["stop_timeout"].format(timeout=config["server"]["stop_timeout"])
        )
    except Exception as e:
        server_in_error = True
        log_exception(f"Error waiting for server shutdown: {e}")
        await set_status("Error")
        return await interaction.followup.send(TRANSLATIONS["stop_error"])

    if exit_code != 0:
        server_in_error = True
        await set_status("Error")
        await interaction.followup.send(
            TRANSLATIONS["stop_error_code"].format(code=exit_code)
        )
    else:
        server_in_error = False
        await set_status("Offline")
        await interaction.followup.send(TRANSLATIONS["stopped"])

    server_process = None


# ===============================
#   /kill
# ===============================
@bot.tree.command(
    name="kill",
    description=TRANSLATIONS["cmd_kill_desc"]
)
async def kill_server(interaction: discord.Interaction):
    global server_process, server_in_error, last_exit_code

    if not server_running():
        return await interaction.response.send_message(TRANSLATIONS["not_running"])

    pid = server_process.pid
    await interaction.response.send_message(
        TRANSLATIONS["killing"].format(pid=pid)
    )
    log(f"=== KILL COMMAND CALLED - PID {pid} ===", "WARN")

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, kill_process_tree, pid)

        await asyncio.sleep(2)

        try:
            if server_process.poll() is None:
                server_process.kill()
            last_exit_code = server_process.poll()
        except Exception as e:
            log(f"Error getting exit code after kill: {e}", "DEBUG")
            last_exit_code = -1

        log(f"Process tree killed. Last exit code: {last_exit_code}", "INFO")

    except Exception as e:
        server_in_error = True
        log_exception(f"Kill failed: {e}")
        await set_status("Error")
        return await interaction.followup.send(TRANSLATIONS["kill_error"])

    server_process = None
    server_in_error = False
    await set_status("Offline")
    await interaction.followup.send(TRANSLATIONS["killed"])


# ===============================
#   /status
# ===============================
@bot.tree.command(
    name="status",
    description=TRANSLATIONS["cmd_status_desc"]
)
async def status_cmd(interaction: discord.Interaction):
    """Display current server status with logs

    Args:
        interaction: Discord interaction object
    """
    global server_in_error, last_exit_code

    running = server_running()

    if running:
        status = f"🟢 {TRANSLATIONS.get('server_online', 'Online')}"
    elif server_in_error:
        status = f"🔴 {TRANSLATIONS.get('server_error', 'Error')}"
    else:
        status = f"⚫ {TRANSLATIONS.get('server_offline', 'Offline')}"

    pid = server_process.pid if running else "—"

    last_lines = read_last_log_lines(config["logging"]["status_log_lines"])

    # Read from server's latest.log instead of server.log
    server_log_path = os.path.join(SERVER_DIR, "logs", "latest.log")
    server_log_info = ""
    if os.path.exists(server_log_path):
        try:
            with open(server_log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                last_5 = "".join(lines[-5:]) if lines else TRANSLATIONS["no_logs"]
                server_log_info = f"\n\n**Server logs - latest.log ({TRANSLATIONS.get('last_lines', 'last 5 lines')}):**\n```{last_5}```"
        except Exception as e:
            log(f"Failed to read latest.log in status command: {e}", "WARN")

    # Add AI personality info if enabled
    personality_info = ""
    if ai_bot and ai_bot.enabled and ai_bot.current_personality:
        personality_info = f"\n**AI Personality:** {ai_bot.current_personality.get('name', 'Unknown')}"

    msg = (
        f"**{TRANSLATIONS['status_label']}:** {status}\n"
        f"**PID:** {pid}\n"
        f"**{TRANSLATIONS['last_exit_code']}:** {last_exit_code if last_exit_code is not None else '—'}{personality_info}\n\n"
        f"**{TRANSLATIONS['recent_logs']} (bot.log):**\n```{last_lines}```{server_log_info}"
    )

    if len(msg) > 1900:
        msg = msg[:1900] + "\n...(truncated)```"

    await interaction.response.send_message(msg)


# ===============================
#   /config
# ===============================
@bot.tree.command(
    name="config",
    description=TRANSLATIONS["cmd_config_desc"]
)
async def config_cmd(interaction: discord.Interaction):
    config_summary = (
        f"**{TRANSLATIONS['config_title']}:**\n"
        f"• {TRANSLATIONS.get('config_language', 'Language')}: `{config['language']}`\n"
        f"• {TRANSLATIONS.get('config_server_dir', 'Server directory')}: `{config['server']['directory']}`\n"
        f"• {TRANSLATIONS.get('config_start_script', 'Start script')}: `{config['server']['start_script']}`\n"
        f"• {TRANSLATIONS.get('config_stop_timeout', 'Stop timeout')}: `{config['server']['stop_timeout']}s`\n"
        f"• {TRANSLATIONS.get('config_log_file', 'Log file')}: `{config['logging']['bot_log_file']}`\n"
    )
    await interaction.response.send_message(config_summary)


# ===============================
#   /logs
# ===============================
@bot.tree.command(
    name="logs",
    description=TRANSLATIONS.get("cmd_logs_desc", "Show last lines from bot.log file")
)
async def logs_cmd(interaction: discord.Interaction):
    """Display recent bot logs

    Args:
        interaction: Discord interaction object
    """
    bot_log_path = LOG_FILE  # bot.log in the same directory as bot.py

    if not os.path.exists(bot_log_path):
        return await interaction.response.send_message(
            TRANSLATIONS.get("logs_not_found", "❌ bot.log file not found. Bot may not have started logging yet.")
        )

    try:
        with open(bot_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_lines = "".join(lines[-30:]) if lines else TRANSLATIONS["no_logs"]

        msg = f"**Bot.log ({TRANSLATIONS.get('last_lines_30', 'last 30 lines')}):**\n```{last_lines}```"

        if len(msg) > 1900:
            msg = msg[:1900] + "\n...(truncated)```"

        await interaction.response.send_message(msg)
    except Exception as e:
        log_exception(f"Error reading bot.log: {e}")
        await interaction.response.send_message(
            f"{TRANSLATIONS.get('logs_read_error', '❌ Error reading bot.log')}: {e}"
        )


# ===============================
#   /personality
# ===============================
@bot.tree.command(
    name="personality",
    description="Change or view AI bot personality"
)
@app_commands.describe(personality="Select a personality")
async def personality_cmd(interaction: discord.Interaction, personality: str = None):
    """Change AI personality"""
    if not ai_bot or not ai_bot.enabled:
        return await interaction.response.send_message(
            TRANSLATIONS.get("ai_disabled", "AI is currently disabled")
        )

    if personality is None:
        # Show current personality and available options
        current = ai_bot.current_personality.get("name", "Unknown")
        available = ai_bot.get_available_personalities()
        available_list = "\n".join([f"• `{key}` - {value}" for key, value in available.items()])

        msg = (
            f"**Current personality:** {current}\n\n"
            f"**Available personalities:**\n{available_list}\n\n"
            f"Use `/personality <name>` to change"
        )
        return await interaction.response.send_message(msg)

    # Load requested personality
    if ai_bot.set_personality(personality):
        personality_name = ai_bot.current_personality.get("name", personality)
        await interaction.response.send_message(
            f"Personality changed to: **{personality_name}**"
        )
        log(f"Personality changed to: {personality}", "INFO")

        # Force status update to show new personality
        global last_status
        last_status = None
        if server_in_error:
            await set_status("Error")
        elif server_running():
            await set_status("Online")
        else:
            await set_status("Offline")
    else:
        available = ai_bot.get_available_personalities()
        available_list = ", ".join(available.keys())
        await interaction.response.send_message(
            f"Personality `{personality}` not found. Available: {available_list}"
        )


# Create autocomplete function for personality choices
@personality_cmd.autocomplete('personality')
async def personality_autocomplete(
        interaction: discord.Interaction,
        current: str,
) -> list[app_commands.Choice[str]]:
    """Provide personality options for autocomplete"""
    if not ai_bot or not ai_bot.enabled:
        return []

    available = ai_bot.get_available_personalities()
    choices = [
        app_commands.Choice(name=name, value=key)
        for key, name in available.items()
        if current.lower() in key.lower() or current.lower() in name.lower()
    ]
    return choices[:25]  # Discord limit


# ===============================
#   /mods
# ===============================
@bot.tree.command(
    name="mods",
    description=TRANSLATIONS.get("cmd_mods_desc", "Show list of installed server mods")
)
@app_commands.describe(refresh="Force refresh the mods cache")
async def mods_cmd(interaction: discord.Interaction, refresh: bool = False):
    """Display list of installed mods

    Args:
        interaction: Discord interaction object
        refresh: Whether to force refresh the cache
    """
    if not ai_bot or not ai_bot.mod_scanner:
        return await interaction.response.send_message(
            TRANSLATIONS.get("mods_disabled", "❌ Mods scanning is not enabled. Enable it in ai-config.json")
        )

    await interaction.response.defer()

    try:
        if refresh:
            log("Refreshing mods cache...", "INFO")
            ai_bot.mod_scanner.scan_mods(force_refresh=True)
            ai_bot.mod_scanner.save_cache()

        mods = ai_bot.mod_scanner.scan_mods()

        if not mods:
            return await interaction.followup.send(
                TRANSLATIONS.get("no_mods", "⚫ No mods found in the server's mods directory.")
            )

        # Build response
        response_lines = [
            f"**{TRANSLATIONS.get('mods_title', 'Installed Mods')}** ({len(mods)} total)"
        ]

        # Show first 40 mods in detail
        for i, mod in enumerate(mods[:40]):
            response_lines.append(f"• **{mod.name}** `v{mod.version}`")

        if len(mods) > 40:
            response_lines.append(f"\n_...and {len(mods) - 40} more mods_")

        response_text = "\n".join(response_lines)

        # Add cache info
        if ai_bot.mod_scanner.last_scan_time:
            scan_time = ai_bot.mod_scanner.last_scan_time.strftime("%Y-%m-%d %H:%M:%S")
            response_text += f"\n\n_{TRANSLATIONS.get('last_scan', 'Last scan')}: {scan_time}_"

        # Split if too long
        if len(response_text) > 2000:
            # Send in chunks
            chunks = []
            current_chunk = response_lines[0] + "\n"

            for line in response_lines[1:]:
                if len(current_chunk) + len(line) + 1 > 1900:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"

            if current_chunk:
                chunks.append(current_chunk)

            await interaction.followup.send(chunks[0])
            for chunk in chunks[1:]:
                await interaction.channel.send(chunk)
        else:
            await interaction.followup.send(response_text)

        log(f"Mods list sent ({len(mods)} mods)", "INFO")

    except Exception as e:
        log_exception(f"Error in mods command: {e}")
        await interaction.followup.send(
            f"{TRANSLATIONS.get('mods_error', '❌ Error reading mods')}: {e}"
        )


# ===============================
#   Background task
# ===============================
@tasks.loop(seconds=15)
async def update_status():
    """Periodically update bot status based on server state"""
    global server_in_error

    try:
        if server_in_error:
            await set_status("Error")
            return

        if server_running():
            await set_status("Online")
        else:
            await set_status("Offline")
    except Exception as e:
        log_exception(f"update_status crashed: {e}")


@update_status.before_loop
async def before_status_loop():
    """Wait for bot to be ready before starting status loop"""
    await bot.wait_until_ready()
    log("Status update loop starting", "INFO")


# ===============================
#   Run bot
# ===============================
if __name__ == "__main__":
    log("=" * 60, "INFO")
    log(f"Minecraft Server Bot v3.5", "INFO")
    log(f"Language: {LANG}", "INFO")
    log(f"Server directory: {SERVER_DIR}", "INFO")
    log(f"Start script: {START_BAT}", "INFO")
    ai_status = "Enabled" if (ai_bot and ai_bot.enabled) else "Disabled"
    personality = ai_bot.personality_key if ai_bot and ai_bot.enabled else "N/A"
    log(f"AI Module: {ai_status} (Personality: {personality})", "INFO")
    log("=" * 60, "INFO")

    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        log("Bot stopped by user (Ctrl+C)", "INFO")
    except Exception as e:
        log_exception(f"Bot crashed: {e}")
        raise
