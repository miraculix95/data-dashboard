# data-dashboard — Roadmap

Live at: [dashboard.ai-devhub-247.site](https://dashboard.ai-devhub-247.site)

---

## Aktueller Stand (v1.3)

- GitHub Trending: Top-Repos der letzten 7 Tage via GitHub Search API
- Wöchentlicher Cache + manueller Refresh-Button
- AI Summary via OpenRouter (Gemini, Grok, GPT-4o, Claude — konfigurierbar)
- README-Kontext pro Repo (erste 2000 Zeichen) für bessere Analyse
- PDF-Export: Trend-Analyse + Tabelle mit klickbaren Links + Anhang mit Repo-Beschreibungen
- Passwortschutz via `st.secrets`
- Prompt-Template in `prompts/github_summary.md` — editierbar ohne Code

---

## Kurzfristig — GitHub Trending Verbesserungen

### Mehrsprachiger Report
Config-Option `summary.language: de/en/fr` bereits vorhanden. Erweiterung: Sprachauswahl direkt im UI (Dropdown), ohne Config-Datei anzufassen.

### Sprach-Filter im UI
Momentan: Freitext-Eingabe. Besser: Dropdown mit den gängigsten Sprachen (Python, TypeScript, Rust, Go, …) + "Alle".

### Zeitraum-Filter
Aktuell fest auf 7 Tage. Option: 24h / 7d / 30d als Buttons. Zeigt andere Trending-Dynamiken.

### E-Mail / Telegram-Versand
"Jetzt als Telegram senden" — Button schickt PDF direkt an Bastian. Kein manuelles Download nötig. Oder: wöchentlicher automatischer Versand per Cron.

### Favoriten / Watchlist
Repos manuell markieren ("interessiert mich") — tauchen auf einer eigenen Seite wieder auf. Persistiert in einer lokalen JSON-Datei.

---

## Mittelfristig — Neue Dashboard-Seiten

Das Dashboard ist als Multi-Page-App gebaut — neue Seite = neue `.py`-Datei in `pages/`.

### Server Status
Docker-Container, Disk Usage, RAM, laufende Services. Alles was `ps aux`, `df -h` und `docker ps` liefern — visuell aufbereitet. Nützlich als schneller Blick ohne SSH.

### ClaudeClaw Logs
Live-Log-Viewer im Browser. Letzte N Heartbeat-Entries, Fehler, laufende Jobs. Filtert nach Level (INFO / WARNING / ERROR). Ersatz für `tail -f` via SSH.

### n8n Workflow Status
Aktive Workflows, letzte Runs, Fehler — via n8n REST API. Quick-Health-Check ohne n8n-UI öffnen zu müssen.

### Kosten-Tracker
API-Verbrauch der letzten 30 Tage: Anthropic, OpenRouter, ElevenLabs, Vercel. Tagesgenau. Alert wenn Monatsbudget zu X% ausgeschöpft.

### YouTube Monitor
*(Abhängig von YouTube Data API v3 — Server-IP ist bei YouTube gesperrt, also kein direktes Scraping)*
Neue Uploads von abonnierten Kanälen — Metadaten, Thumbnails, kurze Zusammenfassung via LLM.

---

## Längerfristig — Tiefere Integration

### HackerNews Trending
Analog zu GitHub: Top-Stories der letzten 24h / 7d, AI-gefiltert nach Relevanz für AI/Dev-Themen. Mit Zusammenfassung und PDF-Export.

### arXiv Paper Digest
Täglicher Scan neuer Papers (cs.AI, cs.LG, cs.CL) nach Keywords. LLM-Zusammenfassung der relevantesten 5 Papers. Wöchentlicher Digest per Telegram.

### Persönliches GitHub-Monitoring
Eigene Repos: neue Commits, Issues, Stars. Gestarnte Repos: neue Releases. Telegram-Notification bei Ereignis.

### Inbox Drop → Auto-Visualisierung
Datei per SFTP in `devhub/inbox/` legen → ClaudeClaw erkennt Typ und verarbeitet:
- `.csv` / `.xlsx` → Daten-Seite im Dashboard automatisch generieren
- `.json` → strukturiert anzeigen, auf Anomalien prüfen

---

## Architektur-Notizen

- Alle neuen Seiten: `pages/<N>_<Name>.py`
- Config-Erweiterungen in `config.yaml`, kein Hardcoding
- Neue Prompts in `prompts/` als separate `.md`-Dateien
- Secrets immer via `st.secrets` oder `devhub/.env`
- Neue API-Keys in `devhub/.env` (geteilt) oder projektlokale `.env`
