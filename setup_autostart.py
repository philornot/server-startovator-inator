"""
Setup script for configuring Minecraft Discord Bot to run on Windows startup.
Uses Windows Task Scheduler to run the bot automatically when the system boots.
"""
import os
import subprocess
import sys
from pathlib import Path


def is_admin():
    """Check if script is running with administrator privileges"""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False


def setup_task_scheduler():
    """Configure Windows Task Scheduler to run bot on startup"""

    # Get paths
    bot_dir = Path(__file__).parent.absolute()
    bot_path = bot_dir / "bot.py"

    # Use pythonw.exe for no console window
    python_path = Path(sys.executable)
    pythonw_path = python_path.parent / "pythonw.exe"

    if not pythonw_path.exists():
        print(f"Error: pythonw.exe not found at {pythonw_path}")
        print("Make sure Python is properly installed.")
        return False

    if not bot_path.exists():
        print(f"Error: bot.py not found at {bot_path}")
        return False

    print("Configuring Windows Task Scheduler...")
    print(f"Bot location: {bot_path}")
    print(f"Python location: {pythonw_path}")
    print()

    # Create scheduled task
    cmd = [
        "schtasks", "/create",
        "/tn", "MinecraftBot",
        "/tr", f'"{pythonw_path}" "{bot_path}"',
        "/sc", "onstart",
        "/rl", "highest",
        "/f"  # Force overwrite if exists
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            print("Success! Bot configured to start automatically on system startup.")
            print()
            print("To start the bot now without rebooting:")
            print("  schtasks /run /tn MinecraftBot")
            print()
            print("To stop the bot:")
            print("  taskkill /f /im pythonw.exe /fi \"WINDOWTITLE eq bot.py*\"")
            print()
            print("To remove autostart:")
            print("  schtasks /delete /tn MinecraftBot /f")
            print()
            return True
        else:
            print(f"Error creating scheduled task:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Minecraft Discord Bot - Autostart Setup")
    print("=" * 60)
    print()

    # Check operating system
    if os.name != 'nt':
        print("Error: This script only works on Windows.")
        print("For other operating systems, please configure autostart manually.")
        return 1

    # Check admin privileges
    if not is_admin():
        print("Warning: This script should be run as Administrator for best results.")
        print("Right-click and select 'Run as administrator'")
        print()
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            print("Aborted.")
            return 1
        print()

    # Setup task
    success = setup_task_scheduler()

    print()
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        input("Press Enter to exit...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
