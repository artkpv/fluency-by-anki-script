#!/usr/bin/env python3
"""
Interactive Anki Card Creator using 'trans' (Translate Shell) - Multilingual
"""

import sys
import os
import json
import subprocess
import requests
import urllib.parse
import re
import time
import base64

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
    except Exception: return False

def card_exists(deck, word):
    safe_word = word.replace('"', '\\"')
    query = f'deck:"{deck}" "Word:{safe_word}"'
    res = invoke('findNotes', query=query)
    return bool(res)

def get_deck_names(): return invoke('deckNames')

def select_deck():
    decks = get_deck_names()
    if not decks: return "Default"
    decks.sort(reverse=True)
    print("\nAvailable Decks:")
    for i, deck in enumerate(decks, 1): print(f"{i}. {deck}")
    while True:
        choice = input(f"\nSelect deck (1-{len(decks)}) [Default]: ").strip()
        if not choice: return "Default"
        if choice.isdigit() and 0 < int(choice) <= len(decks): return decks[int(choice)-1]
        print("Invalid selection.")

def run_trans_dump(word, lang='en'):
    # Use the target language for host language (-hl) to get definitions in that language
    # This ensures "full immersion" definitions.
    cmd = ["trans", "-dump", "-no-ansi", "-s", lang, "-t", lang, "-hl", lang, word]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout.strip()
        start, end = output.find('['), output.rfind(']')
        if start != -1 and end != -1: return json.loads(output[start:end+1])
    except Exception: pass
    return None

def download_audio(word, lang='en'):
    filename = f"anki_audio_{re.sub(r'[^a-zA-Z0-9]', '_', word)}.mp3"
    filepath = os.path.join(TMP_DIR, filename)
    # -speak downloads the original text audio
    subprocess.run(["trans", "-download-audio-as", filepath, "-s", lang, "-speak", "-no-ansi", word], 
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

                        # Collect synonyms for this POS (entries where val is a list)
                        synonyms = []
                        for entry in entries:
                            if isinstance(entry, list) and len(entry) > 0 and isinstance(entry[0], list):
                                synonyms.extend(entry[0][:3])
                        syn_suffix = f" | Synonyms: {', '.join(synonyms[:3])}" if synonyms else ""

                        for entry in entries:
                            if not isinstance(entry, list) or len(entry) == 0: continue
                            val = entry[0]

                            # Definitions are strings; synonym lists are lists
                            if isinstance(val, str):
                                all_pos.add(pos)
                                result["definitions"].append(f"({pos}) {val}{syn_suffix}")
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
    if not check_anki_connection():
        subprocess.run(["dunstify", "-u", "critical", "Anki is not running!"])
        print("Error: Anki is not running.")
        sys.exit(1)
    
    lang_code = input("Target Language Code (e.g. en, fr, tr) [en]: ").strip().lower() or 'en'
    
    deck_name = select_deck()
    print(f"Using deck: {deck_name} | Language: {lang_code}")

    while True:
        try:
            print("\n" + "-"*40)
            word = input("Enter word (or 'q'): ").strip()
            if not word or word.lower() == 'q': break
            
            if card_exists(deck_name, word):
                print(f"Warning: The word '{word}' is already in the deck '{deck_name}'.")
                if input("Add anyway? (y/N): ").strip().lower() != 'y':
                    continue

            print(f"Fetching {lang_code} data...")
            data = parse_trans_data(run_trans_dump(word, lang_code), word)
            audio_path, audio_fn = download_audio(word, lang_code)
            
            target_wiktionary_url = f"https://{lang_code}.wiktionary.org/wiki/{urllib.parse.quote(word)}"
            en_wiktionary_url = f"https://en.wiktionary.org/wiki/{urllib.parse.quote(word)}"
            
            langeek_url = f"https://www.google.com/search?q=site:dictionary.langeek.co+{urllib.parse.quote(word)}"
            subprocess.Popen(["firefox",
                f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(word)}",
                target_wiktionary_url,
                en_wiktionary_url,
                langeek_url],
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
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    invoke('storeMediaFile', filename=audio_fn, data=b64)
                    note["fields"]["Pronunciation sound"] = f"[sound:{audio_fn}]"
            
            if pic_input:
                img_html_list = []
                for idx, img_src in enumerate(pic_input.split(',')):
                    img_src = img_src.strip().strip("'").strip('"')
                    if not img_src: continue
                    
                    # Expand user path (e.g. ~)
                    img_src = os.path.expanduser(img_src)

                    try:
                        img_data = None
                        ext = ".jpg"
                        
                        if img_src.startswith("http"):
                            print(f"Downloading: {img_src}")
                            try:
                                r = requests.get(img_src, timeout=15)
                                if r.status_code == 200:
                                    img_data = r.content
                                    ct = r.headers.get("Content-Type", "").lower()
                                    if "png" in ct: ext = ".png"
                                    elif "gif" in ct: ext = ".gif"
                                    elif "webp" in ct: ext = ".webp"
                                    elif img_src.lower().endswith(".png"): ext = ".png"
                                    elif img_src.lower().endswith(".gif"): ext = ".gif"
                                    elif img_src.lower().endswith(".webp"): ext = ".webp"
                                else:
                                    print(f"Failed to download {img_src}: {r.status_code}")
                            except Exception as e:
                                print(f"Download error {img_src}: {e}")
                        
                        elif os.path.exists(img_src):
                            try:
                                with open(img_src, 'rb') as f:
                                    img_data = f.read()
                                ext = os.path.splitext(img_src)[1] or ".jpg"
                            except Exception as e:
                                print(f"File read error {img_src}: {e}")
                        else:
                            print(f"Warning: Image not found: {img_src}")

                        if img_data:
                            # Use unique filename to avoid collisions
                            fname = f"anki_img_{int(time.time())}_{idx}{ext}"
                            b64 = base64.b64encode(img_data).decode('utf-8')
                            if invoke('storeMediaFile', filename=fname, data=b64):
                                img_html_list.append(f'<img src="{fname}">')
                            else:
                                print(f"Failed to store media: {fname}")

                    except Exception as e:
                        print(f"Error processing {img_src}: {e}")
                
                if img_html_list:
                    note["fields"]["Picture"] = " ".join(img_html_list)

            res = invoke('addNote', note=note)
            print(f"Card added! ID: {res}" if res else "Failed to add card.")
            if audio_path and os.path.exists(audio_path): os.remove(audio_path)

        except KeyboardInterrupt: break
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__": main()