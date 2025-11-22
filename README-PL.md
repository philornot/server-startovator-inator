# Bot Discord do Zarządzania Serwerem Minecraft

Bot na Discorda do zdalnego zarządzania serwerem Minecraft z pełną obsługą wielu języków.

## Funkcje

- **Start/Stop/Kill** - Zdalne sterowanie serwerem Minecraft
- **Monitoring statusu** - Aktualizacje statusu w czasie rzeczywistym przez Discord presence
- **Logowanie** - Logi z timestampami i przechwytywaniem outputu serwera
- **Praca w tle** - Działanie jako usługa Windows lub zaplanowane zadanie
- **Konfigurowalne** - Wszystkie ustawienia w jednym pliku JSON
- **Wielojęzyczność** - Wbudowane tłumaczenia polskie i angielskie

## Wymagania

- Python 3.10 lub nowszy
- Discord.py 2.0 lub nowszy
- Token bota Discord
- Windows (dla skryptów .bat serwera)

## Instalacja

### 1. Zainstaluj Zależności

```bash
pip install -r requirements.txt
```

### 2. Utwórz Konfigurację

```bash
# Skopiuj przykładową konfigurację
copy config.example.json config.json

# Utwórz plik .env dla tokena
echo DISCORD_TOKEN=twoj_token_tutaj > .env
```

### 3. Edytuj Konfigurację

Otwórz `config.json` i skonfiguruj:

- `server.directory` - Ścieżka do folderu serwera Minecraft (użyj `\\` dla ścieżek Windows)
- `server.start_script` - Nazwa skryptu startowego (np. `start-server.bat`)
- `language` - Wybierz `"pl"` lub `"en"`

### 4. Utwórz Bota Discord

1. Przejdź do [Discord Developer Portal](https://discord.com/developers/applications)
2. Utwórz nową aplikację (Create New Application)
3. Przejdź do sekcji Bot i kliknij Add Bot
4. Skopiuj token i wklej go do pliku `.env`
5. Włącz **Message Content Intent** w ustawieniach bota
6. Przejdź do OAuth2 URL Generator:
    - Wybierz scope: `bot`, `applications.commands`
    - Wybierz uprawnienia: `Send Messages`, `Use Slash Commands`
    - Skopiuj wygenerowany URL i zaproś bota na swój serwer

### 5. Uruchom Bota

**Do testów:**

```bash
python bot.py
```

**Do użytku produkcyjnego (praca w tle):**

Zobacz następną sekcję dotyczącą automatycznego uruchamiania.

## Uruchamianie w Tle

Masz dwie opcje uruchamiania bota automatycznie przy starcie Windows.

### Opcja A: Task Scheduler (Zalecane)

Uruchom dołączony skrypt instalacyjny jako Administrator:

```bash
python setup_autostart.py
```

To skonfiguruje Harmonogram Zadań Windows do uruchamiania bota przy starcie systemu.

Aby zarządzać zadaniem:

```bash
# Uruchom bota ręcznie
schtasks /run /tn MinecraftBot

# Zatrzymaj bota
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq bot.py*"

# Usuń autostart
schtasks /delete /tn MinecraftBot /f
```

### Opcja B: NSSM (Zaawansowane)

Dla większej kontroli możesz użyć NSSM (Non-Sucking Service Manager):

1. Pobierz NSSM z oficjalnej strony: https://nssm.cc/download
2. Wypakuj `nssm.exe` z odpowiedniego folderu (`win64` dla systemów 64-bitowych)
3. Otwórz Wiersz polecenia / Powershell jako Administrator
4. Uruchom:

    ```bash
    nssm.exe install MinecraftBot
    ```

5. W GUI NSSM:
    - Application Path: Ścieżka do `python.exe` (np. `C:\Python311\python.exe`)
    - Startup directory: Ścieżka do folderu bota
    - Arguments: `bot.py`

6. Uruchom usługę:

    ```bash
    nssm.exe start MinecraftBot
    ```

**Zarządzanie usługą:**

```bash
# Uruchom usługę
nssm.exe start MinecraftBot

# Zatrzymaj usługę
nssm.exe stop MinecraftBot

# Zrestartuj usługę
nssm.exe restart MinecraftBot

# Sprawdź status usługi
nssm.exe status MinecraftBot

# Usuń usługę
nssm.exe remove MinecraftBot confirm
```

Możesz też zarządzać usługą przez GUI Windows Services (`services.msc`).

NSSM zapewnia dodatkowe funkcje jak automatyczny restart po crashu i szczegółowe logowanie.

## Komendy

| Komenda   | Opis                                          |
|-----------|-----------------------------------------------|
| `/start`  | Uruchom serwer Minecraft                      |
| `/stop`   | Zatrzymaj serwer łagodnie                     |
| `/kill`   | Wymuś zabicie procesu serwera                 |
| `/status` | Pokaż aktualny status serwera i ostatnie logi |
| `/logs`   | Pokaż ostatnie 30 linii z server.log          |
| `/config` | Wyświetl aktualną konfigurację bota           |

## Konfiguracja

### Ustawienia Serwera

```json
{
  "server": {
    "directory": "C:\\sciezka\\do\\minecraft\\server",
    "start_script": "start-server.bat",
    "stop_timeout": 60
  }
}
```

- `directory` - Pełna ścieżka do folderu serwera Minecraft
- `start_script` - Nazwa pliku skryptu startowego
- `stop_timeout` - Sekundy oczekiwania na graceful shutdown (domyślnie: 60)

### Ustawienia Logowania

```json
{
  "logging": {
    "bot_log_file": "bot.log",
    "status_log_lines": 15
  }
}
```

- `bot_log_file` - Ścieżka do pliku logów (domyślnie: "bot.log")
- `status_log_lines` - Liczba linii logów pokazywanych w `/status` (domyślnie: 15)

### Język

```json
{
  "language": "pl"
}
```

Ustaw na `"pl"` dla polskiego lub `"en"` dla angielskiego.

## Dodawanie Nowych Języków

Edytuj `config.json` i dodaj nową sekcję tłumaczeń:

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

Następnie ustaw `"language": "de"` w swojej konfiguracji.

## Aktualizacja Bota

Po zaktualizowaniu kodu (np. przez git pull), zrestartuj bota:

**Jeśli używasz Task Scheduler:**

```bash
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq bot.py*"
schtasks /run /tn MinecraftBot
```

**Jeśli używasz NSSM:**

```bash
nssm.exe restart MinecraftBot
```

## Pliki Logów

- `bot.log` - Aktywność bota i output serwera
- `server/server.log` - Log serwera Minecraft

## Uwagi Bezpieczeństwa

- Nigdy nie commituj pliku `.env` ani rzeczywistego `config.json` do kontroli wersji
- Trzymaj swój token Discord w tajemnicy
- Bot wymaga dostępu do uruchamiania/zatrzymywania procesu serwera
- Upewnij się, że tylko zaufane osoby mają dostęp do komend bota na Discordzie

## Licencja

Licencja MIT — Zobacz plik [LICENSE](LICENSE) dla szczegółów.

---

**Angielski README:** [README.md](README.md)