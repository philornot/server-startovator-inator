# Bot Discord do Zarządzania Serwerem Minecraft

Bot na Discorda do zdalnego zarządzania serwerem Minecraft.

## Funkcje

- **Start/Stop/Kill** - Zdalne sterowanie serwerem Minecraft
- **Monitoring statusu** - Aktualizacje statusu w czasie rzeczywistym
- **Logowanie** - Logi z timestampami i przechwytywaniem outputu serwera
- **Konfigurowalne** - Wszystkie ustawienia w jednym pliku JSON

## Wymagania

- Python 3.10+
- Discord.py 2.0+
- Token bota Discord
- Windows (dla skryptów .bat serwera)

## Instalacja

1. **Sklonuj lub pobierz** to repozytorium

2. **Zainstaluj zależności:**
   ```bash
   pip install discord.py python-dotenv
   ```

3. **Utwórz plik konfiguracyjny:**
   ```bash
   cp config.example.json config.json
   ```

4. **Edytuj `config.json`** i wypełnij ustawienia:
    - `discord_token` - Token twojego bota Discord (lub użyj pliku `.env`)
    - `server.directory` - Ścieżka do folderu serwera Minecraft
    - `server.start_script` - Nazwa skryptu startowego (np. `start-server.bat`)
    - `language` - Wybierz `"pl"` lub `"en"`

5. **Utwórz bota Discord:**
    - Przejdź do [Discord Developer Portal](https://discord.com/developers/applications)
    - Utwórz nową aplikację (Create New Application)
    - Przejdź do sekcji Bot → Add Bot
    - Skopiuj token i wklej do `config.json` lub utwórz plik `.env`:
      ```
      DISCORD_TOKEN=twoj_token_tutaj
      ```
    - Włącz **Message Content Intent** w ustawieniach bota
    - Przejdź do OAuth2 → URL Generator:
        - Wybierz scope: `bot`, `applications.commands`
        - Wybierz uprawnienia: `Send Messages`, `Use Slash Commands`
        - Skopiuj wygenerowany URL i zaproś bota na swój serwer

6. **Uruchom bota:**
   ```bash
   python bot.py
   ```

## Komendy

| Komenda   | Opis                                              |
|-----------|---------------------------------------------------|
| `/start`  | Uruchom serwer Minecraft                          |
| `/stop`   | Zatrzymaj serwer łagodnie (wysyła komendę "stop") |
| `/kill`   | Wymuś zabicie procesu serwera                     |
| `/status` | Pokaż aktualny status serwera i ostatnie logi     |
| `/config` | Wyświetl aktualną konfigurację bota               |

## Opcje Konfiguracji

### Ustawienia Serwera

- `directory` - Pełna ścieżka do folderu serwera Minecraft
- `start_script` - Nazwa pliku skryptu startowego
- `stop_timeout` - Sekundy oczekiwania na graceful shutdown (domyślnie: 60)

### Ustawienia Logowania

- `bot_log_file` - Ścieżka do pliku logów (domyślnie: "bot.log")
- `status_log_lines` - Liczba linii logów pokazywanych w `/status` (domyślnie: 15)

### Język

Ustaw `"language": "pl"` dla polskiego lub `"language": "en"` dla angielskiego

## Dodawanie Nowych Języków

Edytuj `config.json` i dodaj nową sekcję tłumaczeń w `translations`:

```json
"translations": {
    "en": {...},
    "pl": { ...},
    "de": {
        "already_running": "Server läuft bereits.",
        "starting": "Server wird gestartet...",
        ...
    }
}
```

Następnie ustaw `"language": "de"` aby go użyć.

## Rozwiązywanie Problemów

### Bot nie odpowiada na komendy

- Sprawdź czy bot ma odpowiednie uprawnienia na serwerze Discord
- Zweryfikuj czy **Message Content Intent** jest włączony w Discord Developer Portal
- Uruchom komendę `/config` aby sprawdzić czy ustawienia są poprawnie załadowane

### Błąd "config.json not found"

- Skopiuj `config.example.json` do `config.json`
- Edytuj plik swoimi ustawieniami

### Serwer nie chce się uruchomić

- Zweryfikuj czy ścieżka `server.directory` jest poprawna (użyj podwójnych backslashy `\\` na Windows)
- Sprawdź czy `start_script` istnieje w katalogu serwera
- Przejrzyj `bot.log` aby zobaczyć szczegółowe komunikaty błędów

### Status pokazuje "Error" po zatrzymaniu

- Normalne jeśli serwer się crashnął lub został zabity
- Sprawdź ostatni exit code w komendzie `/status`
- Przejrzyj logi serwera aby znaleźć szczegóły crasha

## Licencja

Licencja MIT — Możesz swobodnie modyfikować i dystrybuować

---

**Angielski README:** [README.md](README.md)