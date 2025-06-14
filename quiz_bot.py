import os
import logging
import asyncio
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read API keys from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

if not GOOGLE_API_KEY or not TELEGRAM_TOKEN:
    raise ValueError("Please set GOOGLE_API_KEY and TELEGRAM_TOKEN in .env file")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "\U0001F44B Welcome to the Cucumber + Capybara Quiz Bot!\n\n"
        "Use /quiz to get a new question about Cucumber and Capybara testing.\n"
        "Each question will have three options, and you'll get an explanation for the correct answer."
    )
    await update.message.reply_text(welcome_message)

# Sync function to call Gemini 2.0 Flash with retry
def generate_quiz_question_sync(max_retries=3):
    prompt = """Generate a multiple-choice question about Cucumber and Capybara testing for freshers. \
    The question should have three options and include an explanation for the correct answer.\
    Each option should be one word or a maximum of three words.\
    Format the response as follows:\
    Question: [question text]\
    Options:\
    A) [option 1]\
    B) [option 2]\
    C) [option 3]\
    Correct Answer: [letter]\
    Explanation: [explanation]"""

    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Error in Gemini API (Attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt  # exponential backoff
                time.sleep(sleep_time)
            else:
                return None

# Async wrapper
async def generate_quiz_question():
    return await asyncio.to_thread(generate_quiz_question_sync)

# Parser function
def parse_quiz_response(response_text):
    try:
        question_match = re.search(r'Question:\s*(.*)', response_text)
        question = question_match.group(1).strip() if question_match else "Question not found"

        options = re.findall(r'(A|B|C)\)\s*(.*)', response_text)
        option_buttons = [(letter, text) for letter, text in options]

        correct_match = re.search(r'Correct Answer:\s*([A-C])', response_text)
        correct_answer = correct_match.group(1) if correct_match else None

        explanation_match = re.search(r'Explanation:\s*(.*)', response_text, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else ''

        return question, option_buttons, correct_answer, explanation

    except Exception as e:
        logger.error(f"Error parsing quiz response: {e}")
        return None, [], None, ''

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response_text = await generate_quiz_question()

    if not response_text:
        await update.message.reply_text("Sorry, failed to generate quiz question. Please try again later.")
        return

    question, options, correct_answer, explanation = parse_quiz_response(response_text)

    if not correct_answer or not options:
        await update.message.reply_text("Sorry, could not parse question correctly. Please try again.")
        return

    # Poll-style numbering and display
    option_numbers = {"A": "1", "B": "2", "C": "3"}
    poll_options = "\n".join([
        f"<b>{option_numbers.get(letter, letter)}.</b> {text}" for letter, text in options
    ])
    keyboard = [
        [InlineKeyboardButton(f"{option_numbers.get(letter, letter)}", callback_data=f"{letter}_{correct_answer}")]
        for letter, text in options
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['explanation'] = explanation

    quiz_message = (
        "<b>📊 Poll: Cucumber + Capybara Quiz</b>\n\n"
        f"<b>{question}</b>\n\n"
        f"{poll_options}\n\n"
        "<i>Select the correct option below:</i>"
    )
    await update.message.reply_text(quiz_message, reply_markup=reply_markup, parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_option, correct_answer = query.data.split('_')

    if selected_option == correct_answer:
        message = "<b>✅ Correct!</b> 🎉"
    else:
        message = f"<b>❌ Incorrect!</b> The correct answer is <b>{correct_answer}</b>."

    explanation = context.user_data.get('explanation', '')
    if explanation:
        message += f"\n\n<b>Explanation:</b> {explanation}"

    await query.edit_message_text(text=message, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /quiz to get a quiz question.")

# Main function
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
