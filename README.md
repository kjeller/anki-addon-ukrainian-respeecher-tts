# Ukrainian Audio Generator

An Anki add-on that generates Ukrainian TTS audio for your flashcards using the [Respeecher](https://respeecher.com) Ukrainian Real-Time TTS API generate an audio file, and embeds a `[sound:…]` tag directly into each note.

## Requirements

- Anki 2.1.45 or later
- A [Respeecher API key](https://respeecher.com)

## Build

1. Run `./build.sh` to produce `ukrainian_audio_generator.ankiaddon`.
2. In Anki: **Tools › Add-ons › Install from file…** and select the `.ankiaddon` file.
3. Restart Anki.

## Configuration

Open **Tools › Add-ons**, select *Ukrainian Audio Generator (Respeecher)*, and click **Config**.

| Key | Description | Example |
|-----|-------------|---------|
| `api_key` | Your Respeecher API key | `"your-key-here"` |
| `voice_id` | Voice ID from **List Voices** | `"olesia-conversation"` |
| `source_field` | Note field whose text is sent to TTS | `"Front"` |
| `audio_field` | Field where `[sound:…]` is written. Leave blank to append to `source_field` | `"Audio"` |
| `skip_if_audio_exists` | Skip notes whose target field already contains `[sound:…]` | `true` |

## Usage

1. Set your `api_key` and `voice_id` in the config (see above).
2. To browse available voices: **Tools › Ukrainian Audio Generator › List Voices**.
3. To generate audio: **Tools › Ukrainian Audio Generator › Generate Audio**.
   - A dialog will appear — select which decks to process.
   - Progress is shown note-by-note; audio files are cached so re-runs are fast.
   - A summary (processed / skipped / errors) is shown on completion.

## How it works

- Text is read from `source_field`, stripped of HTML and existing `[sound:…]` tags, then sent to the Respeecher Ukrainian RT TTS API (`https://api.respeecher.com/v1/public/tts/ua-rt/`).
- Audio files are saved to Anki's media folder and named by an MD5 hash of the voice + text, so identical text is never synthesised twice.
- The `[sound:…]` tag is written to `audio_field` if configured, otherwise appended to `source_field`.

## Project structure

```
__init__.py               # Anki add-on entry point (UI, menu, background worker)
respeecher_client.py      # Thin REST client for the Respeecher TTS API
config.json               # Default add-on configuration
config.md                 # Configuration reference (shown in Anki add-on manager)
manifest.json             # Anki add-on metadata
build.sh                  # Packages all files into ukrainian_audio_generator.ankiaddon
```

