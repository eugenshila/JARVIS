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
