# Fix: Starts, Stays for a While, Then Disappears

**Issue:** Starts, stays for a while, then disappears.

**Root Causes:**
1. After callbacks without try/except break chain
2. No WM_DELETE_WINDOW accidental close
3. OneFile temp %TEMP%\_MEI cleanup by antivirus after minutes
4. No logging

**Fixes v0.1.9.4:**
- Logging to ~/.jarvis/jarvis.log
- sys.excepthook stays open
- WM_DELETE_WINDOW Yes=Quit No=Minimize Cancel=Stay open
- keep_alive every 60s checks viewable
- update_clock robust try/except always reschedules
- Onedir MSI with heat harvesting stable

**Quick Fixes:**
1. Check log: type %USERPROFILE%\.jarvis\jarvis.log
2. Run from CMD: python app.py leave open
3. Python portable: pip install -e . && python app.py stays open with keep-alive
4. Frontend: npm run dev circular HUD never disappears
5. Disable antivirus temp cleanup or use onedir MSI
6. Download new MSI v0.1.9.4

**SHILATECH**
