# LinguaLens

![LinguaLens Logo](https://i.imgur.com/aak0ooW.png) 

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.8+-brightgreen)](https://www.python.org/)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-orange)](https://github.com/yourusername/lingualens)

## Overview

**LinguaLens** is an innovative language learning tool designed to make mastering foreign languages intuitive and effective using the **Birkenbihl Method**. It breaks down sentences into word-by-word translations, provides fluent translations, and offers detailed grammar explanations—all in an interactive, user-friendly interface. Built with a Flask backend and a responsive HTML/CSS/JavaScript frontend, LinguaLens is perfect for language learners and developers passionate about educational technology.

### What is the Birkenbihl Method?

Developed by Vera F. Birkenbihl, the Birkenbihl Method focuses on "decoding" foreign languages by first understanding the literal meaning of each word in your native language. This approach strengthens neural connections, making it easier to read and internalize grammar patterns naturally.

## Features

- **Word-by-Word Translation**: Literal translations with preserved word order, paired with fluent translations.
- **Grammar Explanations**: 3-5 key grammar points per sentence, tailored for learners with highlighted terms.
- **Multilingual Support**: Supports numerous languages (e.g., French, Spanish, German, Japanese, and more).
- **Interactive Interface**: Hover for word translations, listen via text-to-speech, and explore grammar with a click.
- **Save & History**: Store translations locally and access them anytime.
- **Dark Mode**: Toggle between light and dark themes.
- **Responsive Design**: Optimized for desktop and mobile.
- **Export Options**: Copy translations to clipboard or download as text files.

## Demo

![LinguaLens Demo](https://i.imgur.com/8BIxjQt.png)

## Installation

### Prerequisites

- **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
- **Google Gemini API Key**: Required for translation and grammar analysis. [Get an API key](https://cloud.google.com/)
- **Web Browser**: Chrome, Firefox, Edge, or similar.

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/lingualens.git
   cd lingualens
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the API Key**
- Open `app.py` and replace the placeholder API key:
  
     ```python
     genai.configure(api_key="YOUR_API_KEY_HERE")
     ```

5. **Run the Application**
   ```bash
   python app.py
   ```
   - Open your browser and go to `http://localhost:5000`.

## Usage

1. **Select Languages**: Choose a source (foreign) and target (native) language from the dropdown menus.
2. **Enter Text**: Paste or type text in the source language (max 5000 characters).
3. **Process Text**: Click "Process Text" to generate translations and grammar insights.
4. **Interact**: 
   - Hover over words for individual translations.
   - Click the headphones icon to hear the sentence.
   - Click the grammar icon for detailed explanations.
5. **Save**: Use "Save Translation" to store results locally for later review.

## Project Structure

```
lingualens/
├── app.py              # Flask backend with API endpoints
├── index.html          # Frontend with HTML, CSS, and JavaScript
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

### Backend (`app.py`)

- **Endpoints**:
  - `/`: Serves `index.html`.
  - `/process`: Generates translations using the Birkenbihl Method.
  - `/grammar-explanation`: Provides grammar analysis for sentences.
- **Tech**: Flask, Google Generative AI, regex.

### Frontend (`index.html`)

- **HTML**: Layout for input, output, and history.
- **CSS**: Custom styles with dark mode and responsive design.
- **JavaScript**: Handles API calls, interactivity, and local storage.

## Contributing

We’d love your help to improve LinguaLens! To contribute:

1. Fork the repository.
2. Create a branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m "Add your feature"`.
4. Push to your fork: `git push origin feature/your-feature`.
5. Submit a Pull Request.

### Contribution Ideas

- Expand language support in `get_language_name()`.
- Enhance error handling for API rate limits.
- Add cloud storage for saved translations.
- Introduce new UI themes or animations.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Vera F. Birkenbihl**: For her groundbreaking language learning methodology.
- **Google Gemini API**: Powers translation and grammar analysis.
- **Open Source Community**: For tools like Flask and Font Awesome.
- **Grok 3, Claude Sonnet 3.7, ChatGPT**: For help in development. 

## Contact

Questions or ideas? Open an issue or reach out:
- Email: [lstrmarti@gmail.com](mailto:email@example.com)
- GitHub: [al1starych](#) <!-- Replace with actual profile -->

---

Happy learning with LinguaLens! 🌍📚

---
