# Cucumber + Capybara Quiz Telegram Bot

This is a Telegram bot that generates multiple-choice quiz questions about Cucumber and Capybara testing. It uses Google Gemini (Generative AI) to create fresh questions and explanations for each answer.

## Features
- Get a new quiz question with /quiz
- Each question has 3 options (1-3 words each)
- Inline buttons for answering, styled like a Telegram poll
- Instant feedback with explanations

## Requirements
- Python 3.8+
- Telegram Bot Token
- Google Generative AI API Key

## Setup
1. **Clone the repository**
2. **Install dependencies:**
   ```bash
   pip install python-telegram-bot google-generativeai python-dotenv
   ```
3. **Create a `.env` file** in the project directory with:
   ```env
   TELEGRAM_TOKEN=your-telegram-bot-token
   GOOGLE_API_KEY=your-google-api-key
   ```
4. **Run the bot:**
   ```bash
   python3 quiz_bot.py
   ```

## Usage
- Start the bot: `/start`
- Get a quiz: `/quiz`
- Get help: `/help`

## Notes
- Each quiz question and its options are generated live by Google Gemini.
- Options are always short (1-3 words).
- The UI mimics Telegram's native poll style.

---

**Author:** Your Name
