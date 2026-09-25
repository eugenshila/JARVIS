"""GUI Launcher for Windows — keeps window open, launches desktop or chat."""

import sys
import os
from pathlib import Path

# Ensure src on path
ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def launch_desktop():
    """Launch Tkinter desktop GUI (stays open)."""
    try:
        # Try to import and run app.py
        sys.path.insert(0, str(ROOT))
        import app
        app.main()
    except Exception as e:
        print(f"Failed to launch desktop GUI: {e}")
        print("Falling back to CLI chat...")
        launch_chat()

def launch_chat():
    """Launch interactive CLI chat."""
    try:
        from jarvis.cli.main import cli
        # Simulate `jarvis chat` command
        sys.argv = ["jarvis", "chat"]
        cli()
    except Exception as e:
        print(f"Chat failed: {e}")
        input("Press Enter to exit...")

def launch_doctor():
    """Run doctor and pause."""
    try:
        from jarvis.cli.main import cli
        sys.argv = ["jarvis", "doctor"]
        cli()
    except Exception as e:
        print(f"Doctor failed: {e}")
    input("\nPress Enter to close...")

if __name__ == "__main__":
    # If launched via double-click, show menu
    if len(sys.argv) == 1:
        print("="*60)
        print("JARVIS - Personal AI, On Personal Devices")
        print("="*60)
        print("")
        print("This is a console app. Run from PowerShell for best experience:")
        print("  jarvis chat")
        print("  jarvis ask \"hello\" --mock")
        print("  jarvis doctor")
        print("")
        print("Launching Desktop GUI...")
        print("")
        try:
            launch_desktop()
        except Exception as e:
            print(f"GUI failed: {e}")
            print("")
            print("Options:")
            print("1. Desktop GUI (Tkinter)")
            print("2. CLI Chat")
            print("3. Doctor")
            print("4. Exit")
            choice = input("Choose (1-4): ").strip()
            if choice == "1":
                launch_desktop()
            elif choice == "2":
                launch_chat()
            elif choice == "3":
                launch_doctor()
    else:
        # Launched with args, e.g., from shortcut
        mode = sys.argv[1] if len(sys.argv) > 1 else "desktop"
        if mode == "desktop":
            launch_desktop()
        elif mode == "chat":
            launch_chat()
        elif mode == "doctor":
            launch_doctor()
        else:
            launch_desktop()
