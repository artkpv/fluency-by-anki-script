# Fluency by Anki Script

An interactive CLI tool for creating English vocabulary Anki cards with definitions, IPA pronunciation, audio, examples, and images.

## Features

- Fetches word definitions and IPA transcription using `trans` (Translate Shell)
- Downloads audio pronunciation automatically
- Opens Google Images and Wiktionary for visual reference
- Supports custom images (URL or local file)
- Interactive editing of all card fields before adding

## Prerequisites

1. **Anki** with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed
2. **[Translate Shell](https://github.com/soimort/translate-shell)** (`trans` command)
3. **Firefox** (for opening reference pages)
4. **Python 3** with `requests` library

### Install dependencies

```bash
# Install translate-shell (Arch Linux)
sudo pacman -S translate-shell

# Or on Ubuntu/Debian
sudo apt install translate-shell

# Install Python dependency
pip install requests
```

## Setup

1. Import the included Anki deck to get the required note type:
   ```
   example anki deck with the card types.apkg
   ```
   This creates the "FF basic vocabulary" note type that the script uses.

2. Make sure Anki is running with AnkiConnect enabled.

## Usage

```bash
python add_anki_card.py
```

1. Select the deck where you want to add cards
2. Enter a word to look up
3. The script will:
   - Fetch definitions, IPA, and examples
   - Download audio pronunciation
   - Open Firefox tabs with Google Images and Wiktionary
4. Edit any fields as needed (or press Enter to keep defaults)
5. Optionally add a picture (URL or local path)
6. Confirm to add the card

Enter `q` to quit.

## Card Fields

| Field | Description |
|-------|-------------|
| Word | The vocabulary word |
| Translation | Definition(s) |
| IPA transcription | Phonetic pronunciation |
| PoS | Part of speech |
| Example sentence(s) | Usage examples |
| Notes | Your personal notes |
| Picture | Image (optional) |
| Pronunciation sound | Audio file (auto-downloaded) |

## License

MIT
