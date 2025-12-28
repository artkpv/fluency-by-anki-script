#!/usr/bin/env python3
"""
Interactive Anki Card Creator using 'trans' (Translate Shell) - English to English
"""

import sys
import os
import json
import subprocess
import requests
import urllib.parse
import re
import time

ANKI_CONNECT_URL = 'http://localhost:8765'
MODEL_NAME = 'FF basic vocabulary'
TMP_DIR = "/tmp"

def invoke(action, **params):
    requestJson = json.dumps({'action': action, 'params': params, 'version': 6})
    try:
        response = requests.post(ANKI_CONNECT_URL, data=requestJson).json()
        if len(response) != 2: return None
        if response['error']: print(f"AnkiConnect Error: {response['error']}")
        return response['result']
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def check_anki_connection():
    try: return requests.get(ANKI_CONNECT_URL).status_code == 200
    except: return False

def get_deck_names(): return invoke('deckNames')

def select_deck():
    decks = get_deck_names()
    if not decks: return "Default"
    print("\nAvailable Decks:")
    for i, deck in enumerate(decks, 1): print(f"{i}. {deck}")
    while True:
        choice = input(f"\nSelect deck (1-{len(decks)}) [Default]: ").strip()
        if not choice: return "Default"
        if choice.isdigit() and 0 < int(choice) <= len(decks): return decks[int(choice)-1]
        print("Invalid selection.")

def run_trans_dump(word):
    # Force English locale to ensure POS and labels are in English
    env = os.environ.copy()
    env["LANG"] = "en_US.UTF-8"
    cmd = ["trans", "-dump", "-no-ansi", "-s", "en", "-t", "en", word]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        output = result.stdout.strip()
        start, end = output.find('['), output.rfind(']')
        if start != -1 and end != -1: return json.loads(output[start:end+1])
    except: pass
    return None

def download_audio(word):
    filename = f"anki_audio_{re.sub(r'[^a-zA-Z0-9]', '_', word)}.mp3"
    filepath = os.path.join(TMP_DIR, filename)
    # -speak downloads the original text audio (English)
    subprocess.run(["trans", "-download-audio-as", filepath, "-s", "en", "-speak", "-no-ansi", word], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return (filepath, filename) if os.path.exists(filepath) and os.path.getsize(filepath) > 0 else (None, None)

def parse_trans_data(data, word):
    result = {"word": word, "translation": "", "ipa": "", "pos": "", "definitions": [], "examples": []}
    if not data: return result

    try:
        # 1. Main Block (IPA)
        if len(data) > 0 and isinstance(data[0], list):
            if len(data[0]) > 1 and isinstance(data[0][1], list) and len(data[0][1]) > 3:
                result["ipa"] = f"/{data[0][1][3]}/"

        # 2. Extract Definitions and Examples
        all_pos = set()
        
        # Priority 1: Explanation-style definitions
        for item in data:
            if isinstance(item, list) and len(item) > 0 and isinstance(item[0], list) and len(item[0]) > 0:
                for pos_block in item:
                    if isinstance(pos_block, list) and len(pos_block) > 1 and isinstance(pos_block[0], str):
                        pos = pos_block[0]
                        entries = pos_block[1]
                        if not isinstance(entries, list): continue
                        
                        for entry in entries:
                            if not isinstance(entry, list) or len(entry) == 0: continue
                            val = entry[0]
                            
                            # Definitions are strings; synonym lists are lists
                            if isinstance(val, str):
                                all_pos.add(pos)
                                result["definitions"].append(f"({pos}) {val}")
                                if len(entry) > 2 and isinstance(entry[2], str):
                                    result["examples"].append(entry[2])

        # Priority 2: Fallback to synonyms if no definitions found
        if not result["definitions"]:
            for item in data:
                if isinstance(item, list) and len(item) > 1 and isinstance(item[0], str):
                    pos = item[0]
                    all_pos.add(pos)
                    synonyms = item[1]
                    if isinstance(synonyms, list):
                        result["definitions"].append(f"({pos}) {', '.join(synonyms[:5])}")

        result["pos"] = ", ".join(all_pos)
        if result["definitions"]:
            result["translation"] = "<br>".join(result["definitions"])

    except Exception as e:
        print(f"Error parsing JSON: {e}")

    return result

def main():
    if not check_anki_connection(): print("Error: Anki is not running."); sys.exit(1)
    deck_name = select_deck()
    print(f"Using deck: {deck_name}")

    while True:
        try:
            print("\n" + "-"*40)
            word = input("Enter word (or 'q'): ").strip()
            if not word or word.lower() == 'q': break
            
            print("Fetching English data...")
            data = parse_trans_data(run_trans_dump(word), word)
            audio_path, audio_fn = download_audio(word)
            
            subprocess.Popen(["firefox", 
                f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(word)}",
                f"https://en.wiktionary.org/wiki/{urllib.parse.quote(word)}"], 
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print("\n--- Card Details ---")
            print(f"IPA: {data['ipa']}")
            print(f"Definitions found: {len(data['definitions'])}")
            
            print(f"Definition:\n{data['translation'].replace('<br>', '\n')}")
            translation = input(f"Edit Definition (Enter to keep): ").strip() or data['translation']
            ipa = input(f"Edit IPA [{data['ipa']}]: ").strip() or data['ipa']
            pos = input(f"Edit PoS [{data['pos']}]: ").strip() or data['pos']
            
            ex_str = "<br>".join([f"• {e}" for e in data['examples'][:4]])
            print(f"Examples found:\n{ex_str.replace('<br>', '\n')}")
            inp = input("Edit Examples (Enter to keep): ").strip()
            if inp: ex_str = inp
            
            notes = input("Notes: ").strip()
            pic_input = input("Picture (URL or Path): ").strip().strip("'" ).strip('"')
            
            if input("Add card? (Y/n): ").lower().strip() == 'n': continue
            
            note = {
                "deckName": deck_name, "modelName": MODEL_NAME,
                "fields": {
                    "Note ID": str(int(time.time() * 1000)),
                    "Word": word, "Translation": translation, "IPA transcription": ipa,
                    "PoS": pos, "Example sentence(s)": ex_str, "Notes": notes,
                    "Article": "", "Gender": "", "Specification term": "", "Article pronunciation": "", "Order": "", "Test spelling?": ""
                },
                "options": {"allowDuplicate": False, "duplicateScope": "deck"},
                "tags": ["script_added"]
            }
            
            if audio_path:
                with open(audio_path, 'rb') as f:
                    b64 = subprocess.run(["base64", "-w0"], input=f.read(), capture_output=True).stdout.decode('utf-8').strip()
                    invoke('storeMediaFile', filename=audio_fn, data=b64)
                    note["fields"]["Pronunciation sound"] = f"[sound:{audio_fn}]"
            
            if pic_input:
                if pic_input.startswith("http"):
                    note["picture"] = [{"url": pic_input, "filename": f"anki_img_{word}.jpg", "fields": ["Picture"]}]
                else:
                    if os.path.exists(pic_input):
                         with open(pic_input, 'rb') as f:
                            b64 = subprocess.run(["base64", "-w0"], input=f.read(), capture_output=True).stdout.decode('utf-8').strip()
                            ext = os.path.splitext(pic_input)[1] or ".jpg"
                            fname = f"anki_img_{int(time.time())}{ext}"
                            invoke('storeMediaFile', filename=fname, data=b64)
                            note["fields"]["Picture"] = f'<img src="{fname}">'
                    else:
                        print(f"Warning: Image file not found: {pic_input}")

            res = invoke('addNote', note=note)
            print(f"Card added! ID: {res}" if res else "Failed to add card.")
            if audio_path and os.path.exists(audio_path): os.remove(audio_path)

        except KeyboardInterrupt: break
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__": main()
