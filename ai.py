"""
AI Integration Module for Minecraft Discord Bot
Handles Gemini API interactions with configurable personalities and context
"""
import json
import os
from datetime import datetime
from typing import Optional, List, Dict

import discord
import google.generativeai as genai

from mod_scanner import ModScanner


class ConversationMemory:
    """Simple conversation memory storage with usernames"""

    def __init__(self, max_messages: int = 50):
        """Initialize conversation memory

        Args:
            max_messages: Maximum number of messages to store per channel
        """
        self.conversations: Dict[int, List[dict]] = {}
        self.max_messages = max_messages

    def add_message(self, channel_id: int, role: str, content: str, username: str = ""):
        """Add message to conversation history

        Args:
            channel_id: Discord channel ID
            role: Message role (user/assistant)
            content: Message content
            username: Username of the sender
        """
        if channel_id not in self.conversations:
            self.conversations[channel_id] = []

        self.conversations[channel_id].append({
            "role": role,
            "content": content,
            "username": username,
            "timestamp": datetime.now().isoformat()
        })

        if len(self.conversations[channel_id]) > self.max_messages:
            self.conversations[channel_id] = self.conversations[channel_id][-self.max_messages:]

    def get_history(self, channel_id: int, limit: int = 20) -> List[dict]:
        """Get conversation history for channel

        Args:
            channel_id: Discord channel ID
            limit: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        if channel_id not in self.conversations:
            return []
        return self.conversations[channel_id][-limit:]

    def clear_history(self, channel_id: int):
        """Clear conversation history for channel

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.conversations:
            del self.conversations[channel_id]


class AIBot:
    """AI personality for bot interactions with configurable personalities"""

    def __init__(self, config: dict, ai_config: dict, translations: dict):
        """Initialize AI with configuration

        Args:
            config: Main bot configuration
            ai_config: AI-specific configuration
            translations: Translation strings
        """
        self.config = config
        self.ai_config = ai_config
        self.translations = translations
        self.model = None
        self.enabled = False
        self.memory = ConversationMemory()
        self.current_personality = {}
        self.mod_scanner = None

        # Get AI config
        self.model_name = ai_config.get("model", "gemini-2.5-flash-lite")
        self.default_personality_key = ai_config.get("default_personality", "depressed")

        # Load saved personality or default
        self.current_personality_key = ai_config.get("current_personality", self.default_personality_key)

        # Initialize mod scanner if enabled
        context_config = ai_config.get("context", {})
        if context_config.get("include_mods_list", False):
            try:
                server_dir = config["server"]["directory"]
                cache_duration = context_config.get("mods_cache_duration", 300)
                self.mod_scanner = ModScanner(server_dir, cache_duration)
                self.mod_scanner.load_cache()
                print(f"[INFO] Mod scanner initialized (cache: {cache_duration}s)")
            except Exception as e:
                print(f"[WARN] Failed to initialize mod scanner: {e}")

        # Try to initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)

                # Configure generation with higher token limit
                generation_config = {
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,  # Increased from default
                }

                self.model = genai.GenerativeModel(
                    self.model_name,
                    generation_config=generation_config
                )
                self.enabled = True
                self.load_personality(self.current_personality_key)
                print(f"[INFO] Gemini AI enabled (model: {self.model_name})")
                print(f"[INFO] Current personality: {self.current_personality_key}")
            except Exception as e:
                print(f"[ERROR] Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            print("[WARN] GEMINI_API_KEY not found - AI responses disabled")

    def load_personality(self, personality_key: str) -> bool:
        """Load personality by key

        Args:
            personality_key: Key of the personality to load

        Returns:
            True if personality was loaded successfully
        """
        lang = self.config.get("language", "en")
        personalities = self.ai_config.get("personalities", {}).get(lang, {})

        if personality_key not in personalities:
            print(f"[WARN] Personality '{personality_key}' not found for language '{lang}'")
            return False

        personality_data = personalities[personality_key]
        prompt_path = personality_data.get("prompt", "")

        try:
            if prompt_path.startswith("file://"):
                file_path = prompt_path.replace("file://", "")
                with open(file_path, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
            else:
                prompt_text = prompt_path

            self.current_personality = {
                "key": personality_key,
                "name": personality_data.get("name", personality_key),
                "prompt": prompt_text
            }
            self.personality_key = personality_key

            # Clear all conversation memories when changing personality
            self.memory = ConversationMemory()

            print(f"[INFO] Personality loaded: {self.current_personality['name']}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to load personality: {e}")
            return False

    def get_available_personalities(self) -> Dict[str, str]:
        """Get available personalities for current language

        Returns:
            Dictionary mapping personality keys to display names
        """
        lang = self.config.get("language", "en")
        personalities = self.ai_config.get("personalities", {}).get(lang, {})
        return {
            key: data.get("name", key)
            for key, data in personalities.items()
        }

    def get_server_status_context(self, server_running: bool, server_in_error: bool,
                                  last_exit_code: Optional[int], server_process,
                                  server_dir: str) -> str:
        """Get current server status for AI context

        Args:
            server_running: Whether the server is running
            server_in_error: Whether the server is in an error state
            last_exit_code: Last server exit code
            server_process: Server process object
            server_dir: Server directory path

        Returns:
            Formatted server status string
        """
        status = "Online" if server_running else "Error" if server_in_error else "Offline"
        pid = server_process.pid if server_process and server_running else "N/A"
        exit_code = last_exit_code if last_exit_code is not None else "N/A"

        return f"Server: {status} | PID: {pid} | Exit code: {exit_code}"

    def format_conversation_history(self, channel_id: int, include_usernames: bool = True) -> str:
        """Format conversation history for context

        Args:
            channel_id: Discord channel ID
            include_usernames: Whether to include usernames in history

        Returns:
            Formatted conversation history string
        """
        context_config = self.ai_config.get("context", {})
        limit = context_config.get("chat_history_limit", 15)
        history = self.memory.get_history(channel_id, limit=limit)

        if not history:
            return "No previous conversation."

        formatted = []
        for msg in history:
            if msg["role"] == "assistant":
                formatted.append(f"You: {msg['content']}")
            else:
                username = msg.get("username", "User") if include_usernames else "User"
                formatted.append(f"{username}: {msg['content']}")

        return "\n".join(formatted)

    def get_server_logs_context(self, server_dir: str) -> tuple[str, bool]:
        """Get recent server logs for context

        Args:
            server_dir: Server directory path

        Returns:
            Tuple of (formatted server logs string, logs_available boolean)
        """
        context_config = self.ai_config.get("context", {})
        if not context_config.get("include_server_logs", False):
            return "", False

        # Prefer logs/latest.log, fallback to server.log
        candidates = [
            os.path.join(server_dir, "logs", "latest.log"),
            os.path.join(server_dir, "server.log"),
        ]

        for log_file in candidates:
            if not os.path.exists(log_file):
                continue

            try:
                limit = context_config.get("server_logs_limit", 10)
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                recent_logs = "".join(lines[-limit:]) if lines else ""

                if recent_logs:
                    header = " (from latest.log)" if log_file.endswith("latest.log") else ""
                    return f"\nRecent server logs{header}:\n{recent_logs}", True
                else:
                    return f"\n[SERVER LOGS: Not available - {os.path.basename(log_file)} is empty]", False

            except Exception as e:
                print(f"[WARN] Failed to read server logs from {log_file}: {e}")
                return f"\n[SERVER LOGS: Not available - error reading file: {e}]", False

        return "\n[SERVER LOGS: Not available - no log files found]", False

    def get_mods_context(self) -> str:
        """Get installed mods list for context

        Returns:
            Formatted mods list string
        """
        context_config = self.ai_config.get("context", {})
        if not context_config.get("include_mods_list", False) or not self.mod_scanner:
            return ""

        try:
            max_mods = context_config.get("mods_list_limit", 30)
            mods = self.mod_scanner.scan_mods()

            if not mods:
                return "\nInstalled mods: None"

            mods_list = [f"\nInstalled mods ({len(mods)} total):"]
            for i, mod in enumerate(mods[:max_mods]):
                mods_list.append(f"  • {mod.name} v{mod.version}")

            if len(mods) > max_mods:
                mods_list.append(f"  ... and {len(mods) - max_mods} more")

            return "\n".join(mods_list)

        except Exception as e:
            print(f"[WARN] Failed to get mods context: {e}")
            return ""

    async def generate_response(self, message: discord.Message, history: List[discord.Message],
                                server_running: bool, server_in_error: bool,
                                last_exit_code: Optional[int], server_process,
                                server_dir: str) -> str:
        """Generate AI response using Gemini

        Args:
            message: Discord message that triggered the response
            history: Message history
            server_running: Whether the server is running
            server_in_error: Whether the server is in an error state
            last_exit_code: Last server exit code
            server_process: Server process object
            server_dir: Server directory path

        Returns:
            Generated AI response text
        """

        if not self.enabled or not self.model or not self.current_personality:
            return self._get_fallback_response()

        try:
            channel_id = message.channel.id
            context_config = self.ai_config.get("context", {})

            # Build context
            server_status = self.get_server_status_context(
                server_running, server_in_error, last_exit_code,
                server_process, server_dir
            )

            # Get conversation history
            include_usernames = context_config.get("include_usernames", True)
            conversation_history = self.format_conversation_history(channel_id, include_usernames)

            # Get server logs if enabled
            server_logs, logs_available = self.get_server_logs_context(server_dir)

            # Get mods list if enabled
            mods_context = self.get_mods_context()

            # Build full prompt with context awareness
            context_notes = []
            if not logs_available:
                context_notes.append(
                    "NOTE: Server logs are currently not available. Do NOT make up or assume log contents.")

            context_note_str = "\n" + "\n".join(context_notes) if context_notes else ""

            system_prompt = self.current_personality.get("prompt", "")

            full_prompt = f"""{system_prompt}

Current server status: {server_status}

Previous conversation:
{conversation_history}{server_logs}{mods_context}{context_note_str}

User ({message.author.name}): {message.content}

Respond naturally and be thorough with your answer:"""

            # Generate response
            response = self.model.generate_content(full_prompt)

            if response.text:
                response_text = response.text.strip()

                # Store in memory
                self.memory.add_message(channel_id, "user", message.content, message.author.name)
                self.memory.add_message(channel_id, "assistant", response_text)

                print(f"[INFO] AI response generated for {message.author.name} ({len(response_text)} chars)")
                return response_text
            else:
                return self._get_error_response("empty_response")

        except Exception as e:
            print(f"[ERROR] Gemini API error: {e}")
            import traceback
            traceback.print_exc()
            return self._get_error_response("api_error")

    def _get_fallback_response(self) -> str:
        """Get fallback response when AI is disabled

        Returns:
            Fallback message string
        """
        lang = self.config.get("language", "en")

        if lang == "pl":
            return "AI wyłączone. Użyj komend jak `/status` lub `/start`."
        else:
            return "AI disabled. Use commands like `/status` or `/start`."

    def _get_error_response(self, error_type: str) -> str:
        """Get error response message

        Args:
            error_type: Type of error that occurred

        Returns:
            Error message string
        """
        lang = self.config.get("language", "en")

        if lang == "pl":
            return "Błąd AI. Spróbuj użyć normalnych komend."
        else:
            return "AI error. Try using normal commands."

    def set_personality(self, personality_key: str) -> bool:
        """Set personality and save to config

        Args:
            personality_key: Key of the personality to load

        Returns:
            True if personality was loaded and saved successfully
        """
        if self.load_personality(personality_key):
            # Update config and save
            self.ai_config["current_personality"] = personality_key
            return save_ai_config(self.ai_config, "ai-config.json")
        return False

    def refresh_mods_cache(self) -> bool:
        """Force refresh of mods cache

        Returns:
            True if refresh was successful
        """
        if not self.mod_scanner:
            return False

        try:
            self.mod_scanner.scan_mods(force_refresh=True)
            self.mod_scanner.save_cache()
            print("[INFO] Mods cache refreshed")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to refresh mods cache: {e}")
            return False


def load_ai_config(config_file: str = "ai-config.json") -> dict:
    """Load AI configuration from file

    Args:
        config_file: Path to AI configuration file

    Returns:
        AI configuration dictionary
    """
    if not os.path.exists(config_file):
        print(f"[WARN] AI configuration file '{config_file}' not found")
        return {"enabled": False}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {config_file}: {e}")
        return {"enabled": False}
    except Exception as e:
        print(f"[ERROR] Failed to load {config_file}: {e}")
        return {"enabled": False}


def save_ai_config(ai_config: dict, config_file: str = "ai-config.json"):
    """Save AI configuration to file

    Args:
        ai_config: AI configuration dictionary
        config_file: Path to AI configuration file
    """
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(ai_config, f, indent=2, ensure_ascii=False)
        print(f"[INFO] AI configuration saved to {config_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save AI configuration: {e}")
        return False
