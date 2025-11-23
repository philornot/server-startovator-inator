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


class ConversationMemory:
    """Simple conversation memory storage with usernames"""

    def __init__(self, max_messages: int = 50):
        self.conversations: Dict[int, List[dict]] = {}
        self.max_messages = max_messages

    def add_message(self, channel_id: int, role: str, content: str, username: str = ""):
        """Add message to conversation history"""
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
        """Get conversation history for channel"""
        if channel_id not in self.conversations:
            return []
        return self.conversations[channel_id][-limit:]

    def clear_history(self, channel_id: int):
        """Clear conversation history for channel"""
        if channel_id in self.conversations:
            del self.conversations[channel_id]


class AIBot:
    """AI personality for bot interactions with configurable personalities"""

    def __init__(self, config: dict, ai_config: dict, translations: dict):
        """Initialize AI with configuration"""
        self.config = config
        self.ai_config = ai_config
        self.translations = translations
        self.model = None
        self.enabled = False
        self.memory = ConversationMemory()
        self.current_personality = {}
        self.personality_key = "depressed"  # Default personality key

        # Get AI config
        self.model_name = ai_config.get("model", "gemini-2.0-flash-exp")
        self.default_personality_key = ai_config.get("default_personality", "depressed")

        # Try to initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.enabled = True
                self.load_personality(self.default_personality_key)
                print(f"[INFO] Gemini AI enabled (model: {self.model_name})")
                print(f"[INFO] Default personality: {self.personality_key}")
            except Exception as e:
                print(f"[ERROR] Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            print("[WARN] GEMINI_API_KEY not found - AI responses disabled")

    def load_personality(self, personality_key: str) -> bool:
        """Load personality by key"""
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
                "emoji": personality_data.get("emoji", "🤖"),
                "prompt": prompt_text
            }
            self.personality_key = personality_key
            print(f"[INFO] Personality loaded: {self.current_personality['name']}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to load personality: {e}")
            return False

    def get_available_personalities(self) -> Dict[str, str]:
        """Get available personalities for current language"""
        lang = self.config.get("language", "en")
        personalities = self.ai_config.get("personalities", {}).get(lang, {})
        return {
            key: data.get("emoji", "🤖") + " " + data.get("name", key)
            for key, data in personalities.items()
        }

    def get_server_status_context(self, server_running: bool, server_in_error: bool,
                                  last_exit_code: Optional[int], server_process,
                                  server_dir: str) -> str:
        """Get current server status for AI context"""
        status = "Online" if server_running else "Error" if server_in_error else "Offline"
        pid = server_process.pid if server_process and server_running else "N/A"
        exit_code = last_exit_code if last_exit_code is not None else "N/A"

        return f"Server: {status} | PID: {pid} | Exit code: {exit_code}"

    def format_conversation_history(self, channel_id: int, include_usernames: bool = True) -> str:
        """Format conversation history for context"""
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

    def get_server_logs_context(self, server_dir: str) -> str:
        """Get recent server logs for context"""
        context_config = self.ai_config.get("context", {})
        if not context_config.get("include_server_logs", False):
            return ""

        log_file = os.path.join(server_dir, "server.log")
        if not os.path.exists(log_file):
            return ""

        try:
            limit = context_config.get("server_logs_limit", 10)
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_logs = "".join(lines[-limit:]) if lines else ""

            if recent_logs:
                return f"\nRecent server logs:\n{recent_logs}"
            return ""

        except Exception as e:
            print(f"[WARN] Failed to read server logs: {e}")
            return ""

    async def generate_response(self, message: discord.Message, history: List[discord.Message],
                                server_running: bool, server_in_error: bool,
                                last_exit_code: Optional[int], server_process,
                                server_dir: str) -> str:
        """Generate AI response using Gemini"""

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
            server_logs = self.get_server_logs_context(server_dir)

            # Build full prompt
            system_prompt = self.current_personality.get("prompt", "")

            full_prompt = f"""{system_prompt}

Current server status: {server_status}

Previous conversation:
{conversation_history}{server_logs}

User ({message.author.name}): {message.content}

Respond naturally and briefly:"""

            # Generate response
            response = self.model.generate_content(full_prompt)

            if response.text:
                response_text = response.text.strip()

                # Store in memory
                self.memory.add_message(channel_id, "user", message.content, message.author.name)
                self.memory.add_message(channel_id, "assistant", response_text)

                print(f"[INFO] AI response generated for {message.author.name}")
                return response_text
            else:
                return self._get_error_response("empty_response")

        except Exception as e:
            print(f"[ERROR] Gemini API error: {e}")
            import traceback
            traceback.print_exc()
            return self._get_error_response("api_error")

    def _get_fallback_response(self) -> str:
        """Get fallback response when AI is disabled"""
        lang = self.config.get("language", "en")

        if lang == "pl":
            return "AI wyłączone. Użyj komend jak `/status` lub `/start`."
        else:
            return "AI disabled. Use commands like `/status` or `/start`."

    def _get_error_response(self, error_type: str) -> str:
        """Get error response message"""
        lang = self.config.get("language", "en")

        if lang == "pl":
            return "Błąd AI. Spróbuj użyć normalnych komend."
        else:
            return "AI error. Try using normal commands."


def load_ai_config(config_file: str = "ai-config.json") -> dict:
    """Load AI configuration from file"""
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
