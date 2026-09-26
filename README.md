# Jarvis desktop prototype

A small Windows friendly desktop assistant built with Python's standard library. It can browse a local prompt library, prepare meeting briefs from details you paste, copy prompts, and ask an OpenAI compatible chat API to draft a response. The app runs without an API key in copy mode.

## Run

1. Install Python 3.10 or newer from python.org, including Tkinter.
2. Download or clone this repository.
3. Run `python app.py` from its folder.

For AI responses, set `OPENAI_API_KEY` in your environment before launching. The default endpoint is `https://api.openai.com/v1/chat/completions`, and the default model is `gpt-4o-mini`. You can override these with `JARVIS_API_URL` and `JARVIS_MODEL`. The API key stays in the environment and is never written to project files. API calls send the prompt and pasted context to your chosen provider.

To use [Jarvis Public Prompts](https://github.com/mihaiwillberich/jarvis-public-prompts), download its ZIP from GitHub, extract it, and select its root directory using **Open prompt folder**. The app reads Markdown files locally and extracts the first fenced prompt under `## The prompt`. It also ships with an original meeting brief starter prompt, so you can try it immediately.

## Current scope

This first version accepts pasted meeting details and files you choose as context. It does not automatically read your screen, calendar, email, or contacts. Add those integrations only after choosing the provider and permissions you want. It does not send email or modify calendar events.

The external prompt library is maintained separately and is MIT licensed; if you redistribute a copied set of its prompts, include its LICENSE file.

## Hermes local agent

JARVIS supports Hermes as a local agent through Ollama. Install Ollama, download the model, then run:

```bash
ollama pull nous-hermes2:10.7b
jarvis chat --engine hermes
```

Use `OLLAMA_MODEL` or `JARVIS_MODEL` to select another Hermes-compatible model. The MSI does not bundle the multi-gigabyte model; install it separately on the target Windows machine.

## Low-memory profile (8 GB RAM)

The example configuration now defaults to Ollama with `llama3.2:3b`, which is the recommended everyday model for an 8 GB computer. Install the model on the target machine with:

```bash
ollama pull llama3.2:3b
```

For coding, switch temporarily to:

```bash
ollama pull qwen2.5-coder:3b
JARVIS_MODEL=qwen2.5-coder:3b jarvis chat --engine ollama
```

On Windows PowerShell:

```powershell
ollama pull llama3.2:3b
$env:JARVIS_MODEL="llama3.2:3b"
jarvis.exe chat --engine ollama
```

### Automatic Windows Ollama setup

From the JARVIS project folder, double-click `deploy\windows\SETUP-OLLAMA.bat`. It checks Ollama, starts the Ollama app if needed, installs `llama3.2:3b`, verifies the local API, and launches JARVIS with the lightweight model.
