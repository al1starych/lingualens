from flask import Flask, request, Response, send_file, jsonify
import google.generativeai as genai
import re
import json
import os
import time

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/process', methods=['POST'])
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
    model = genai.GenerativeModel("gemini-2.0-flash")
    
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
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    sentence = data['sentence']
    source_lang = data.get('sourceLang', 'fr')
    target_lang = data.get('targetLang', 'en')
    
    explanation = generate_grammar_explanation(sentence, source_lang, target_lang, model)
    return jsonify(explanation)

def generate_grammar_explanation(sentence, source_lang, target_lang, model):
    prompt = f"""
    Analyze the grammar of this {get_language_name(source_lang)} sentence for a {get_language_name(target_lang)} speaker:
    
    "{sentence}"
    
    Provide 3-5 clear grammar points that would help a learner understand the structure of this sentence.
    For each point:
    1. Identify a specific grammar concept or pattern
    2. Explain it briefly in accessible language
    3. Show how it's used in the example sentence
    
    Use ** around key terms or phrases that should be highlighted.
    
    Format your response as a JSON object with a 'points' array containing each grammar point as a string. Note that you should give your answer in {get_language_name(target_lang)}.
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # If direct JSON extraction fails, try to parse response as JSON
            return json.loads(response_text)
        except Exception as e:
            # If parsing fails, create a formatted response
            print(f"Error parsing grammar explanation JSON: {e}")
            print(f"Raw response: {response_text}")
            points = response_text.split('\n\n')
            return {
                "points": [p.strip() for p in points if p.strip()],
                "error": f"Error parsing response: {e}"
            }
    except Exception as e:
        print(f"Error generating grammar explanation: {e}")
        return {
            "points": ["Unable to generate grammar explanation. Please try again."],
            "error": f"Error: {e}"
        }

def process_sentence(sentence, source_lang, target_lang, model):
    # Check if romanization is needed (for Chinese, Japanese, Korean)
    needs_romanization = source_lang in ['zh', 'ja', 'ko']
    
    romanization_request = ""
    if needs_romanization:
        romanization_type = "pinyin" if source_lang == "zh" else "romaji" if source_lang == "ja" else "romanized Korean"
        romanization_request = f"""
        5. romanization: The {romanization_type} pronunciation guide for the original text
        """
    
    # Form the prompt for the Gemini model
    prompt = f"""
    Process this {get_language_name(source_lang)} sentence using the Birkenbihl method for a {get_language_name(target_lang)} speaker:
    
    "{sentence}"
    
    Return a JSON object with the following fields:
    1. original: The original sentence
    2. wordByWord: A word-by-word literal translation preserving original word order
    3. fluentTranslation: A natural, fluent translation of the sentence
    4. wordTranslations: A dictionary mapping each word in the original to its translation
    {romanization_request}
    
    IMPORTANT: 
    - Provide all translations (wordByWord and fluentTranslation) in {get_language_name(target_lang)}
    - Make sure the wordByWord translation has EXACTLY the same number of words as the original sentence
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

        # Split the original sentence into words
        original_words = sentence.split()
        print(f"Original words: {len(original_words)} - {original_words}")

        # Clean punctuation from words for lookup in wordTranslations
        # For example, "sei," becomes "sei" for dictionary lookup
        cleaned_original_words = [re.sub(r'[.,!?;:"\'-]', '', word) for word in original_words]

        # Initialize the word-by-word translation list
        word_by_word_words = []

        # For each original word, find its translation
        for idx, (orig_word, cleaned_word) in enumerate(zip(original_words, cleaned_original_words)):
            # Check if the cleaned word exists in wordTranslations
            if cleaned_word in result.get('wordTranslations', {}):
                translation = result['wordTranslations'][cleaned_word]
                # If the original word had punctuation, append it to the translation
                if orig_word != cleaned_word:
                    # Extract punctuation from the original word
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
        'en': 'English', 'fr': 'French', 'es': 'Spanish', 'de': 'German',
        'it': 'Italian', 'ja': 'Japanese', 'ru': 'Russian', 'zh': 'Chinese',
        'ar': 'Arabic', 'pt': 'Portuguese', 'hi': 'Hindi', 'ko': 'Korean'
    }
    return languages.get(code, code)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
