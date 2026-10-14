#!/bin/python3

import os
from pathlib import Path
from openai import OpenAI

def translate_html_content(html_content, locale_code, options=None):
    """Sends the HTML body to GPT-6 Luna to translate the visible text layer."""
    local_options = dict(options) if options else {}
    model = local_options.pop("model", "gpt-6-luna")
    effort = local_options.get('reasoning_effort', 'low')
    max_tokens = local_options.get('max_completion_tokens', 25000)

    # Required payload cleanup for the GPT-6 reasoning series
    local_options.pop("temperature", None)
    local_options.pop("top_p", None)

    # Locale mapping dictionary to guide the model's regional language targets
    language_mapping = {
        "es": "Spanish from Spain (es-ES)",
        "fr": "French from France (fr-FR)",
        "it": "Italian (it-IT)",
        "de": "German (de-DE)",
        "pt": "Portuguese (pt-PT)"
    }
    target_language = language_mapping.get(locale_code.lower(), locale_code)

    untranslated_terms = ["chain", "snapshot", "subsnapshot", "ZS3", "MIDI-learn", "MIDI-learning", "program-change", "plugin"]

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a professional technical translator and software localization expert with specialization in audio, MIDI and music production.\n"
                f"Translate this user guide section from English into {target_language}.\n"
                "STRICT RULES:\n"
                "1. Maintain a formal, clear, and instructive tone appropriate for user documentation.\n"
                "2. DO NOT alter or translate any HTML tags, classes, IDs, or structural attributes (href, src, etc.).\n"
                "3. Translate exclusively the human-readable text contents.\n"
                "4. DO NOT translate specialized terms related to audio, MIDI and music production nor other technical terms not commonly translated in specialized articles and news.\n"
                f"5. DO NOT translate zynthian-specific or technical terms like {', '.join([f"'{term}'" for term in untranslated_terms])}.\n"
                "6. Return ONLY the translated raw HTML code. Do not wrap the output in markdown code blocks (```html)."
            )
        },
        {"role": "user", "content": html_content}
    ]

    try:
        client = OpenAI(api_key=OPENAI_APIKEY)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            reasoning_effort=effort,
            max_completion_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        return None

def translate_help_pages(root_directories, target_locales, options=None):
    """
    Recursively scans specified directories, translates HTML files, 
    and saves them in subfolders named after the target locale codes.
    """
    for root_dir in root_directories:
        root_path = Path(root_dir)
        
        if not root_path.exists() or not root_path.is_dir():
            print(f"⚠️ Directory does not exist or is invalid: {root_dir}")
            continue
            
        print(f"\n📂 Scanning directory tree recursively: {root_path.resolve()}")
        
        # rglob("*.html") finds all HTML files at any structural depth level
        for html_file in root_path.rglob("*.html"):
            
            # 🛡️ ANTI-LOOP FILTER: Skip files that are already inside a generated locale subdirectory
            if any(part.lower() in target_locales for part in html_file.parts):
                continue
                
            print(f"\n📄 Found original source file: {html_file.relative_to(root_path)}")
            
            # Read the original source file once for all target languages
            try:
                original_content = html_file.read_text(encoding="utf-8")
                source_mtime = html_file.stat().st_mtime
            except Exception as e:
                print(f"❌ Could not read file {html_file.name}: {e}")
                continue
            
            # Iterate and generate translations for each configured locale
            for locale in target_locales:
                # Target language subfolder relative to the current file location
                locale_folder = html_file.parent / locale
                
                # Automatically create the folder path if it does not exist yet
                locale_folder.mkdir(parents=True, exist_ok=True)
                
                # The output path preserves the original clean filename (e.g., config.html)
                final_output_path = locale_folder / html_file.name

                # Place this right after defining final_output_path:
                if final_output_path.exists():
                    # Skip if the existing translation file is newer than the source file
                    if final_output_path.stat().st_mtime >= source_mtime:
                        print(f"   Skip [{locale}] -> Already up to date.")
                        continue
                    else:
                        print(f"   🔄 Update detected -> Re-translating [{locale}]...")

                print(f"   -> Translating to [{locale}] -> Target path: {final_output_path.relative_to(root_path)}")
                translated_content = translate_html_content(original_content, locale, options)
                
                if translated_content:
                    try:
                        final_output_path.write_text(translated_content, encoding="utf-8")
                    except Exception as e:
                        print(f"   ❌ Error writing output file for [{locale}]: {e}")
                else:
                    print(f"   ⚠️ File generation skipped for [{locale}] due to translation failure.")


def get_openai_apikey():
    try:
        sdir = Path(__file__).resolve().parent
        with open(f"{sdir}/OPENAI.APIKEY", 'r', encoding='utf-8') as f:
            apikey = f.read().strip()
            #print(f"OPENAI APIKEY => {apikey}")
            return apikey
    except:
        pass

# --- SCRIPT EXECUTION CONFIGURATION ---
if __name__ == "__main__":
    # Base target folders containing your documentation structure
    TARGET_DIRECTORIES = [
        "./common",
        "./V4",
        "./Z2"
    ]
    
    # 🌍 Set the list of target locale codes you wish to compile
    LOCALES_TO_GENERATE = ["es", "de", "pt"]
    #LOCALES_TO_GENERATE = ["es"]

    OPENAI_CONFIG = {
        "model": "gpt-6-luna",
        "reasoning_effort": "low",
        "max_completion_tokens": 30000
    }

    OPENAI_APIKEY = get_openai_apikey()
    
    # Run the comprehensive localization process
    translate_help_pages(TARGET_DIRECTORIES, LOCALES_TO_GENERATE, options=OPENAI_CONFIG)

