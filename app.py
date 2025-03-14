from flask import Flask, request, Response, send_file, jsonify
import google.generativeai as genai
import re
import json
import os
import time

app = Flask(__name__)

# Configure the Gemini API
genai.configure(api_key="AIzaSyAwaGJum3kiEysiE0W9qagzMvATW43dWn0")  # Replace with your actual API key
model = genai.GenerativeModel("gemini-2.0-flash")

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/process', methods=['POST'])
def process_text():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    text = data['text']
    source_lang = data.get('sourceLang', 'fr')
    target_lang = data.get('targetLang', 'en')
    sentences = split_into_sentences(text, source_lang)
    
    def generate():
        for sentence in sentences:
            if sentence.strip():
                result = process_sentence(sentence, source_lang, target_lang)
                yield json.dumps(result) + '\n'
                time.sleep(4)  # Add a delay to avoid hitting API rate limits
    
    return Response(generate(), mimetype='application/json')


@app.route('/grammar-explanation', methods=['POST'])
def get_grammar_explanation():
    data = request.get_json()
    
    if not data or 'sentence' not in data:
        return jsonify({'error': 'No sentence provided'}), 400
    
    sentence = data['sentence']
    source_lang = data.get('sourceLang', 'fr')
    target_lang = data.get('targetLang', 'en')
    
    explanation = generate_grammar_explanation(sentence, source_lang, target_lang)
    return jsonify(explanation)

def generate_grammar_explanation(sentence, source_lang, target_lang):
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

# Updated function to properly handle different languages' sentence structures
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

def process_sentence(sentence, source_lang, target_lang):
    # Check if romanization is needed (for Chinese, Japanese, Korean)
    needs_romanization = source_lang in ['zh', 'ja', 'ko']
    
    romanization_request = ""
    if needs_romanization:
        romanization_type = "pinyin" if source_lang == "zh" else "romaji" if source_lang == "ja" else "romanized Korean"
        romanization_request = f"""
        5. romanization: The {romanization_type} pronunciation guide for the original text
        """
    
    prompt = f"""
    Process this {get_language_name(source_lang)} sentence using the Birkenbihl method for a {get_language_name(target_lang)} speaker:
    
    "{sentence}"
    
    Return a JSON object with the following fields:
    1. original: The original sentence
    2. wordByWord: A word-by-word literal translation preserving original word order
    3. fluentTranslation: A natural, fluent translation of the sentence
    4. wordTranslations: A dictionary mapping each word in the original to its translation
    {romanization_request}
    
    IMPORTANT: Provide all translations (wordByWord and fluentTranslation) in {get_language_name(target_lang)}.

    Example format (if source language is French and target language is English):
    {{
        "original": "Je mange une pomme",
        "wordByWord": "I eat an apple",
        "fluentTranslation": "I am eating an apple",
        "wordTranslations": {{
            "je": "I",
            "mange": "eat",
            "une": "an",
            "pomme": "apple"
        }}
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        try:
            json_match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(response_text)
        except:
            # Create a default response structure
            result = {
                "original": sentence,
                "wordByWord": "Translation unavailable",
                "fluentTranslation": "Translation unavailable",
                "wordTranslations": {}
            }
            # Add romanization field if needed
            if needs_romanization:
                result["romanization"] = "Romanization unavailable"
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

def get_language_name(code):
    languages = {
        'en': 'English', 'fr': 'French', 'es': 'Spanish', 'de': 'German',
        'it': 'Italian', 'ja': 'Japanese', 'ru': 'Russian', 'zh': 'Chinese',
        'ar': 'Arabic', 'pt': 'Portuguese', 'hi': 'Hindi', 'ko': 'Korean'
    }
    return languages.get(code, code)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
