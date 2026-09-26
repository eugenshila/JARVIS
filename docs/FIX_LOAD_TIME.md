# Fix: Load Time Too Long

Issue: onefile 50-80MB extracts 100+ files to temp each launch 5-15 sec on i5-6300U HDD.

Fix v0.1.9.5: Build both onefile (slow but simple) + onedir with heat harvesting fast 1-2 sec.

- onefile MSI: single exe contains all, slow load 5-15 sec, fixes python311.dll + disappearing
- onedir MSI with heat: heat.exe dir dist/jarvis-portable -cg ProductComponents -dr INSTALLFOLDER -gg -srd -out files.wxs includes _internal\python311.dll, fast 1-2 sec, fixes load time + python311.dll + disappearing
- Python portable: python app.py fastest 1 sec
- Frontend: npm run dev instant

For i5-6300U: use onedir MSI fast or python app.py or frontend.

SHILATECH
