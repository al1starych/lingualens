from flask import Flask, request, Response, send_file, jsonify, session, redirect, url_for, render_template_string
import google.generativeai as genai
import re
import json
import os
import time
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lingualens_secret_key')  # Set a secret key for sessions

# File to store paid email addresses
PAID_EMAILS_FILE = 'paid_emails.txt'

# Create the file if it doesn't exist
if not os.path.exists(PAID_EMAILS_FILE):
    with open(PAID_EMAILS_FILE, 'w') as f:
        f.write('')  # Create empty file

def is_email_verified(email):
    """Check if the email is in the paid emails list"""
    if not email:
        return False
        
    try:
        with open(PAID_EMAILS_FILE, 'r') as f:
            paid_emails = [line.strip().lower() for line in f.readlines()]
            return email.lower() in paid_emails
    except Exception as e:
        print(f"Error checking email verification: {e}")
        return False

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'verified_email' not in session:
            return redirect(url_for('verification_page'))
        return f(*args, **kwargs)
    return decorated_function

def uses_non_latin_script(lang_code):
    """
    Determines if a language primarily uses a non-Latin writing system.
    
    Args:
        lang_code: The ISO 639-1 or 639-2 language code
        
    Returns:
        bool: True if the language uses a non-Latin script, False otherwise
    """
    # Languages that use non-Latin scripts
    non_latin_scripts = {
        # East Asian scripts
        'zh': 'Chinese (Hanzi)',
        'ja': 'Japanese (Kanji, Hiragana, Katakana)',
        'ko': 'Korean (Hangul)',
        
        # Cyrillic script
        'ru': 'Russian',
        'uk': 'Ukrainian',
        'be': 'Belarusian',
        'bg': 'Bulgarian',
        'sr': 'Serbian (Cyrillic)',
        'mk': 'Macedonian',
        'kk': 'Kazakh',
        'ky': 'Kyrgyz',
        'mn': 'Mongolian (Cyrillic)',
        'tg': 'Tajik',
        
        # Arabic script
        'ar': 'Arabic',
        'fa': 'Persian (Farsi)',
        'ur': 'Urdu',
        'ps': 'Pashto',
        'sd': 'Sindhi',
        'ug': 'Uyghur',
        'ckb': 'Kurdish (Sorani)',
        'ms-Arab': 'Malay (Jawi)',
        
        # Indic scripts
        'hi': 'Hindi (Devanagari)',
        'bn': 'Bengali',
        'ta': 'Tamil',
        'te': 'Telugu',
        'mr': 'Marathi',
        'ne': 'Nepali',
        'pa': 'Punjabi (Gurmukhi)',
        'gu': 'Gujarati',
        'or': 'Odia',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'si': 'Sinhala',
        'sa': 'Sanskrit',
        
        # Other scripts
        'th': 'Thai',
        'lo': 'Lao',
        'km': 'Khmer',
        'my': 'Burmese (Myanmar)',
        'am': 'Amharic',
        'ti': 'Tigrinya',
        'he': 'Hebrew',
        'yi': 'Yiddish',
        'ka': 'Georgian',
        'hy': 'Armenian',
        'el': 'Greek',
        'dv': 'Dhivehi (Thaana)',
        
        # Ethiopic script
        'am': 'Amharic',
        'ti': 'Tigrinya',
        
        # Other scripts
        'bo': 'Tibetan',
        'dz': 'Dzongkha',
    }
    
    return lang_code in non_latin_scripts

@app.route('/')
def verification_page():
    """Show the verification page when accessing the root URL"""
    if 'verified_email' in session:
        return redirect(url_for('app_page'))
    
    with open('verify.html', 'r') as f:
        return f.read()

@app.route('/app')
@login_required
def app_page():
    """Main application page, requires login"""
    return send_file('index.html')

@app.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify if an email is in the paid list"""
    data = request.get_json()
    email = data.get('email', '').strip()
    
    if is_email_verified(email):
        session['verified_email'] = email
        return jsonify({'verified': True})
    else:
        return jsonify({'verified': False})

@app.route('/process', methods=['POST'])
@login_required
def process_text():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    # Get API key from request
    api_key = data.get('apiKey')
    if not api_key:
        return jsonify({'error': 'API key is required'}), 400
    
    # Configure the Gemini API with the user's API key
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
    
    text = data['text']
    source_lang = data.get('sourceLang', 'fr')
    target_lang = data.get('targetLang', 'en')
    sentences = split_into_sentences(text, source_lang)
    
    def generate():
        for sentence in sentences:
            if sentence.strip():
                result = process_sentence(sentence, source_lang, target_lang, model)
                yield json.dumps(result) + '\n'
                time.sleep(4)  # Add a delay to avoid hitting API rate limits
    
    return Response(generate(), mimetype='application/json')

@app.route('/grammar-explanation', methods=['POST'])
@login_required
def get_grammar_explanation():
    data = request.get_json()
    
    if not data or 'sentence' not in data:
        return jsonify({'error': 'No sentence provided'}), 400
    
    # Get API key from request
    api_key = data.get('apiKey')
    if not api_key:
        return jsonify({'error': 'API key is required'}), 400
    
    # Configure the Gemini API with the user's API key
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
    
    sentence = data['sentence']
    source_lang = data.get('sourceLang', 'fr')
    target_lang = data.get('targetLang', 'en')
    
    explanation = generate_grammar_explanation(sentence, source_lang, target_lang, model)
    return explanation

@app.route('/logout')
def logout():
    """Log out the user by clearing the session"""
    session.pop('verified_email', None)
    return redirect(url_for('verification_page'))

def generate_grammar_explanation(sentence, source_lang, target_lang, model):
    prompt = f"""
    Analyze this {get_language_name(source_lang)} sentence in detail for a {get_language_name(target_lang)} speaker:
    
    "{sentence}"
    
    Provide the following (in {get_language_name(target_lang)}):
    1. **Structural Explanation**: Break down the sentence structure.
    2. **Word-by-Word Translation**: List each word with its reading, meaning and grammatical explanation if any. 
    3. **Grammar Points**: List grammar patterns with their difficulty level and frequency of usage. 
    
    Use ** around key terms or phrases that should be highlighted.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
     
    except Exception as e:
        print(f"Error generating grammar explanation: {e}")
        return {
            "points": ["Unable to generate grammar explanation. Please try again."],
            "error": f"Error: {e}"
        }

def process_sentence(sentence, source_lang, target_lang, model):
    # Check if romanization is needed for non-Latin script languages
    needs_romanization = uses_non_latin_script(source_lang)
    
    romanization = ""
    if needs_romanization:
        # First, get the romanization
        romanization_prompt = f"""
        Provide the romanized pronunciation guide for the following {get_language_name(source_lang)} sentence using the most widely accepted romanization standard for this language:
        "{sentence}"
        Return only the romanized text.
        """
        romanization_response = model.generate_content(romanization_prompt)
        romanization = romanization_response.text.strip()
    
    # Use the romanized text for word-by-word translation if available
    text_to_process = romanization if needs_romanization else sentence
    
    # Form the prompt for the Gemini model
    prompt = f"""
    Process this {get_language_name(source_lang)} sentence using the Birkenbihl method for a {get_language_name(target_lang)} speaker. The sentence is provided in {'romanized form' if needs_romanization else 'original form'}.
    
    Original sentence: "{sentence}"
    {'Romanized sentence: "' + romanization + '"' if needs_romanization else ''}
    Text to process: "{text_to_process}"
    
    Return a JSON object with the following fields:
    1. original: The original sentence
    2. wordByWord: A word-by-word literal translation preserving original word order
    3. fluentTranslation: A natural, fluent translation of the sentence
    4. wordTranslations: A dictionary mapping each word in the original to its translation
    {'5. romanization: The romanized pronunciation guide for the original text' if needs_romanization else ''}
    
    IMPORTANT: 
    - Provide all translations (wordByWord and fluentTranslation) in {get_language_name(target_lang)}
    - Make sure the wordByWord translation has EXACTLY the same number of words as the text to process
    - If a single source word translates to multiple target words, hyphenate them (e.g., "bonjour" -> "good-morning")
    - If multiple source words translate to one target word, repeat the target word for each source word
    """
    
    try:
        # Send request to Gemini model
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            result = json.loads(response_text)

        # Split the text to process into words (use romanized text if available)
        text_to_split = romanization if needs_romanization else sentence
        original_words = text_to_split.split()
        print(f"Words to process: {len(original_words)} - {original_words}")

        # Clean punctuation from words for lookup in wordTranslations
        cleaned_original_words = [re.sub(r'[.,!?;:"\'-]', '', word) for word in original_words]

        # Initialize the word-by-word translation list
        word_by_word_words = []

        # For each word, find its translation
        for idx, (orig_word, cleaned_word) in enumerate(zip(original_words, cleaned_original_words)):
            # Check if the cleaned word exists in wordTranslations
            if cleaned_word in result.get('wordTranslations', {}):
                translation = result['wordTranslations'][cleaned_word]
                # If the original word had punctuation, append it to the translation
                if orig_word != cleaned_word:
                    punctuation = orig_word[len(cleaned_word):]
                    translation += punctuation
                word_by_word_words.append(translation)
            else:
                # If the word is not in wordTranslations, translate it individually
                print(f"Word '{cleaned_word}' not found in wordTranslations, requesting translation...")
                word_prompt = f"""
                Translate the word "{cleaned_word}" from {get_language_name(source_lang)} to {get_language_name(target_lang)} in the context of the sentence: "{sentence}"
                Provide the translation as a single word or a hyphenated phrase if necessary. Return only the translation.
                """
                word_response = model.generate_content(word_prompt)
                word_translation = word_response.text.strip()
                print(f"Translated '{cleaned_word}' to '{word_translation}'")

                # If the original word had punctuation, append it to the translation
                if orig_word != cleaned_word:
                    punctuation = orig_word[len(cleaned_word):]
                    word_translation += punctuation
                word_by_word_words.append(word_translation)
                # Update wordTranslations for future reference
                result.setdefault('wordTranslations', {})[cleaned_word] = word_translation

        # Update the wordByWord field with the correct number of words
        result['wordByWord'] = ' '.join(word_by_word_words)
        print(f"Updated wordByWord words: {len(word_by_word_words)} - {word_by_word_words}")
        print(f"Updated wordByWord: {result['wordByWord']}")

        # Verify the word count matches
        if len(original_words) != len(word_by_word_words):
            print(f"Warning: Word count mismatch after processing! Original: {len(original_words)}, WordByWord: {len(word_by_word_words)}")

        # Ensure romanization is included in the result
        if needs_romanization:
            result['romanization'] = romanization

        return result

    except Exception as e:
        print(f"Error processing sentence: {e}")
        result = {
            "original": sentence,
            "wordByWord": "Error processing translation",
            "fluentTranslation": "Error processing translation",
            "wordTranslations": {}
        }
        if needs_romanization:
            result["romanization"] = "Romanization unavailable"
        return result

def split_into_sentences(text, language=None):
    # Define language-specific sentence ending patterns
    east_asian_langs = ['zh', 'ja', 'ko']
    
    if language in east_asian_langs:
        # Chinese/Japanese/Korean sentence endings - includes both full-width and half-width punctuation
        # 。- Chinese/Japanese period, ！- exclamation, ？- question mark, 
        # ；- semicolon, ．- full-width period, etc.
        pattern = r'(?<=[。！？…．；\!\?\.])+'
    else:
        # Western language sentence endings - requires space after punctuation
        pattern = r'(?<=[.!?])\s+'
    
    # Split the text using the appropriate pattern
    sentences = re.split(pattern, text)
    
    # Handle case of very long text with no proper sentence endings
    result = []
    for sentence in sentences:
        if len(sentence) > 200:  # If sentence is too long, try to break it further
            # Use commas, semicolons, or line breaks as secondary breaking points
            subsents = re.split(r'(?<=[,;，；])\s*', sentence)
            result.extend([s for s in subsents if s.strip()])
        else:
            if sentence.strip():
                result.append(sentence)
    
    return result

def get_language_name(code):
    languages = {
        'ab': 'Abkhaz',
        'ace': 'Acehnese',
        'ach': 'Acholi',
        'aa': 'Afar',
        'af': 'Afrikaans',
        'sq': 'Albanian',
        'alr': 'Alur',
        'am': 'Amharic',
        'ar': 'Arabic',
        'hy': 'Armenian',
        'as': 'Assamese',
        'av': 'Avar',
        'awa': 'Awadhi',
        'ay': 'Aymara',
        'az': 'Azerbaijani',
        'ban': 'Balinese',
        'bal': 'Baluchi',
        'bm': 'Bambara',
        'bci': 'Baoulé',
        'ba': 'Bashkir',
        'eu': 'Basque',
        'btk': 'Batak Karo',
        'bts': 'Batak Simalungun',
        'tbw': 'Batak Toba',
        'be': 'Belarusian',
        'bem': 'Bemba',
        'bn': 'Bengali',
        'bew': 'Betawi',
        'bho': 'Bhojpuri',
        'bik': 'Bikol',
        'bs': 'Bosnian',
        'br': 'Breton',
        'bg': 'Bulgarian',
        'bua': 'Buryat',
        'yue': 'Cantonese',
        'ca': 'Catalan',
        'ceb': 'Cebuano',
        'ch': 'Chamorro',
        'ce': 'Chechen',
        'ny': 'Chichewa',
        'zh-Hans': 'Chinese (Simplified)',
        'zh-Hant': 'Chinese (Traditional)',
        'chk': 'Chuukese',
        'cv': 'Chuvash',
        'co': 'Corsican',
        'crh': 'Crimean Tatar (Cyrillic)',
        'crh-Latn': 'Crimean Tatar (Latin)',
        'hr': 'Croatian',
        'cs': 'Czech',
        'da': 'Danish',
        'prs': 'Dari',
        'dv': 'Dhivehi',
        'din': 'Dinka',
        'doi': 'Dogri',
        'dug': 'Dombe',
        'nl': 'Dutch',
        'dyu': 'Dyula',
        'dz': 'Dzongkha',
        'en': 'English',
        'eo': 'Esperanto',
        'et': 'Estonian',
        'ee': 'Ewe',
        'fo': 'Faroese',
        'fj': 'Fijian',
        'fil': 'Filipino',
        'fi': 'Finnish',
        'fon': 'Fon',
        'fr': 'French',
        'fr-CA': 'French (Canada)',
        'fy': 'Frisian',
        'fur': 'Friulian',
        'ff': 'Fulani',
        'gaa': 'Ga',
        'gl': 'Galician',
        'ka': 'Georgian',
        'de': 'German',
        'el': 'Greek',
        'gn': 'Guarani',
        'gu': 'Gujarati',
        'ht': 'Haitian Creole',
        'hak': 'Hakha Chin',
        'ha': 'Hausa',
        'haw': 'Hawaiian',
        'he': 'Hebrew',
        'hil': 'Hiligaynon',
        'hi': 'Hindi',
        'hmn': 'Hmong',
        'hu': 'Hungarian',
        'hrx': 'Hunsrik',
        'iba': 'Iban',
        'is': 'Icelandic',
        'ig': 'Igbo',
        'ilo': 'Ilocano',
        'id': 'Indonesian',
        'iu': 'Inuktut (Latin)',
        'iu-Syll': 'Inuktut (Syllabics)',
        'ga': 'Irish',
        'it': 'Italian',
        'jam': 'Jamaican Patois',
        'ja': 'Japanese',
        'jv': 'Javanese',
        'kac': 'Jingpo',
        'kl': 'Kalaallisut',
        'kn': 'Kannada',
        'kr': 'Kanuri',
        'pam': 'Kapampangan',
        'kk': 'Kazakh',
        'kha': 'Khasi',
        'km': 'Khmer',
        'ki': 'Kiga',
        'kg': 'Kikongo',
        'rw': 'Kinyarwanda',
        'ktu': 'Kituba',
        'trp': 'Kokborok',
        'kv': 'Komi',
        'kok': 'Konkani',
        'ko': 'Korean',
        'kri': 'Krio',
        'ku': 'Kurdish (Kurmanji)',
        'ckb': 'Kurdish (Sorani)',
        'ky': 'Kyrgyz',
        'lo': 'Lao',
        'ltg': 'Latgalian',
        'la': 'Latin',
        'lv': 'Latvian',
        'lij': 'Ligurian',
        'li': 'Limburgish',
        'ln': 'Lingala',
        'lt': 'Lithuanian',
        'lmo': 'Lombard',
        'lg': 'Luganda',
        'luo': 'Luo',
        'lb': 'Luxembourgish',
        'mk': 'Macedonian',
        'mad': 'Madurese',
        'mai': 'Maithili',
        'mak': 'Makassar',
        'mg': 'Malagasy',
        'ms': 'Malay',
        'ms-Arab': 'Malay (Jawi)',
        'ml': 'Malayalam',
        'mt': 'Maltese',
        'mam': 'Mam',
        'gv': 'Manx',
        'mi': 'Maori',
        'mr': 'Marathi',
        'mh': 'Marshallese',
        'mfe': 'Mauritian Creole',
        'mhr': 'Meadow Mari',
        'mni': 'Meiteilon (Manipuri)',
        'min': 'Minang',
        'lus': 'Mizo',
        'mn': 'Mongolian',
        'my': 'Myanmar (Burmese)',
        'nah': 'Nahuatl (Eastern Huasteca)',
        'ndc': 'Ndau',
        'nr': 'Ndebele (South)',
        'new': 'Nepalbhasa (Newari)',
        'ne': 'Nepali',
        'nqo': 'NKo',
        'no': 'Norwegian (Bokmål)',
        'nus': 'Nuer',
        'oc': 'Occitan',
        'or': 'Odia (Oriya)',
        'om': 'Oromo',
        'os': 'Ossetian',
        'pag': 'Pangasinan',
        'pap': 'Papiamento',
        'ps': 'Pashto',
        'fa': 'Persian',
        'pl': 'Polish',
        'pt-BR': 'Portuguese (Brazil)',
        'pt-PT': 'Portuguese (Portugal)',
        'pa': 'Punjabi (Gurmukhi)',
        'pa-Arab': 'Punjabi (Shahmukhi)',
        'qu': 'Quechua',
        'kek': 'Qʼeqchiʼ',
        'rom': 'Romani',
        'ro': 'Romanian',
        'rn': 'Rundi',
        'ru': 'Russian',
        'se': 'Sami (North)',
        'sm': 'Samoan',
        'sg': 'Sango',
        'sa': 'Sanskrit',
        'sat': 'Santali (Latin)',
        'sat-Olck': 'Santali (Ol Chiki)',
        'gd': 'Scots Gaelic',
        'nso': 'Sepedi',
        'sr': 'Serbian',
        'st': 'Sesotho',
        'crs': 'Seychellois Creole',
        'shn': 'Shan',
        'sn': 'Shona',
        'scn': 'Sicilian',
        'szl': 'Silesian',
        'sd': 'Sindhi',
        'si': 'Sinhala',
        'sk': 'Slovak',
        'sl': 'Slovenian',
        'so': 'Somali',
        'es': 'Spanish',
        'su': 'Sundanese',
        'sus': 'Susu',
        'sw': 'Swahili',
        'ss': 'Swati',
        'sv': 'Swedish',
        'ty': 'Tahitian',
        'tg': 'Tajik',
        'ber': 'Tamazight',
        'ber-Tfng': 'Tamazight (Tifinagh)',
        'ta': 'Tamil',
        'tt': 'Tatar',
        'te': 'Telugu',
        'tet': 'Tetum',
        'th': 'Thai',
        'bo': 'Tibetan',
        'ti': 'Tigrinya',
        'tiv': 'Tiv',
        'tpi': 'Tok Pisin',
        'to': 'Tongan',
        'lua': 'Tshiluba',
        'ts': 'Tsonga',
        'tn': 'Tswana',
        'tcy': 'Tulu',
        'tum': 'Tumbuka',
        'tr': 'Turkish',
        'tk': 'Turkmen',
        'tyv': 'Tuvan',
        'tw': 'Twi',
        'udm': 'Udmurt',
        'uk': 'Ukrainian',
        'ur': 'Urdu',
        'ug': 'Uyghur',
        'uz': 'Uzbek',
        've': 'Venda',
        'vec': 'Venetian',
        'vi': 'Vietnamese',
        'war': 'Waray',
        'cy': 'Welsh',
        'wo': 'Wolof',
        'xh': 'Xhosa',
        'sah': 'Yakut',
        'yi': 'Yiddish',
        'yo': 'Yoruba',
        'yua': 'Yucatec Maya',
        'zap': 'Zapotec',
        'zu': 'Zulu'
    }
    return languages.get(code, code)

if __name__ == '__main__':
    # Ensure the paid emails file exists
    if not os.path.exists(PAID_EMAILS_FILE):
        with open(PAID_EMAILS_FILE, 'w') as f:
            f.write('')
            
    app.run(debug=True, host='0.0.0.0', port=5000)
