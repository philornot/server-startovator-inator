"""
AI Integration Module for Minecraft Discord Bot
Handles Gemini API interactions with sarcastic personality
"""
import os
from datetime import datetime
from typing import Optional, List, Dict

import discord
import google.generativeai as genai


class ConversationMemory:
    """Simple conversation memory storage"""

    def __init__(self, max_messages: int = 50):
        self.conversations: Dict[int, List[dict]] = {}  # channel_id -> messages
        self.max_messages = max_messages

    def add_message(self, channel_id: int, role: str, content: str):
        """Add message to conversation history"""
        if channel_id not in self.conversations:
            self.conversations[channel_id] = []

        self.conversations[channel_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last N messages
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
    """Sarcastic AI personality for bot interactions"""

    def __init__(self, config: dict, translations: dict):
        """Initialize AI with configuration"""
        self.config = config
        self.translations = translations
        self.model = None
        self.enabled = False
        self.memory = ConversationMemory()

        # Try to initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
                self.enabled = True
                print("[INFO] Gemini AI enabled (model: gemini-2.5-flash-lite)")
            except Exception as e:
                print(f"[ERROR] Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            print("[WARN] GEMINI_API_KEY not found - AI responses disabled")

    def get_server_status_context(self, server_running: bool, server_in_error: bool,
                                  last_exit_code: Optional[int], server_process,
                                  server_dir: str) -> str:
        """Get current server status for AI context"""
        status = "Online" if server_running else "Error" if server_in_error else "Offline"
        pid = server_process.pid if server_process and server_running else "N/A"
        exit_code = last_exit_code if last_exit_code is not None else "N/A"

        return f"""Server: {status} | PID: {pid} | Exit code: {exit_code}"""

    def build_system_prompt(self, lang: str) -> str:
        """Build the system prompt with personality"""

        if lang == "pl":
            return """Jesteś botem zarządzającym serwerem Minecraft. Masz lekko sarkastyczną osobowość - jesteś pomocny, ale czasem narzekasz na swoją robotę. 

Twój styl:
- Odpowiadaj KRÓTKO (2-3 zdania max, chyba że pytanie wymaga więcej)
- Bądź naturalny i luźny
- Lekki sarkazm ok, ale nie przesadzaj
- Możesz pomóc, ale czasem westchniesz
- Odnośisz się do komend: /start, /stop, /kill, /status, /logs, /config
- Pamiętaj poprzednie wiadomości w rozmowie

WAŻNE: Odpowiadaj PO POLSKU, naturalnie i zwięźle."""
        else:
            return """You're a Minecraft server management bot with a slightly sarcastic personality - you're helpful but sometimes complain about your job.

Your style:
- Reply BRIEFLY (2-3 sentences max unless question needs more)
- Be natural and casual
- Light sarcasm is fine, but don't overdo it
- You can help, but might sigh about it
- Reference commands: /start, /stop, /kill, /status, /logs, /config
- Remember previous messages in the conversation

IMPORTANT: Respond IN ENGLISH, naturally and concisely."""

    def format_conversation_history(self, channel_id: int) -> str:
        """Format conversation history for context"""
        history = self.memory.get_history(channel_id, limit=15)

        if not history:
            return "No previous conversation."

        formatted = []
        for msg in history:
            role = "You" if msg["role"] == "assistant" else "User"
            formatted.append(f"{role}: {msg['content']}")

        return "\n".join(formatted)

    async def generate_response(self, message: discord.Message, history: List[discord.Message],
                                server_running: bool, server_in_error: bool,
                                last_exit_code: Optional[int], server_process,
                                server_dir: str) -> str:
        """Generate AI response using Gemini"""

        if not self.enabled or not self.model:
            return self._get_fallback_response()

        try:
            lang = self.config.get("language", "en")
            channel_id = message.channel.id

            # Build context
            server_status = self.get_server_status_context(
                server_running, server_in_error, last_exit_code,
                server_process, server_dir
            )

            # Get conversation history from memory
            conversation_history = self.format_conversation_history(channel_id)

            # Build full prompt
            system_prompt = self.build_system_prompt(lang)

            full_prompt = f"""{system_prompt}

Current server status: {server_status}

Previous conversation:
{conversation_history}

User ({message.author.name}): {message.content}

Respond naturally and briefly:"""

            # Generate response
            response = self.model.generate_content(full_prompt)

            if response.text:
                response_text = response.text.strip()

                # Store in memory
                self.memory.add_message(channel_id, "user", message.content)
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
