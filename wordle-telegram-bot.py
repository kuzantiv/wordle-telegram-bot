#!/usr/bin/env python

import logging
from dotenv import load_dotenv
import os

from telegram import Update, ForceReply, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PicklePersistence, CallbackQueryHandler

from WordlePlugin import Wordle, GameState
from markups import *
import Config as config
# from ImageExport import ImageExport

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> (None):
    """Send a message when the command /start is issued."""
    config.log_new_user(update, context)
    config.send_start_message(update, context)

    context.user_data["name"] = update.message.from_user.first_name
    context.user_data["user_id"] = update.message.from_user.id
    help_command(update, context)

# def change_language(update: Update, context: CallbackContext) -> (None):
#     """show buttons to choose a language"""
#     query = update.callback_query
#     if query == None:
#         msg_out = f"Choose a language, current language is: " + context.user_data.get("language", "german")
#         menu_msg = context.user_data.get('menu_msg')
#         menu_msg.delete()
#         menu_msg = update.message.reply_text(msg_out, reply_markup=language_menu_markup)
#         update.message.reply_text(text=msg_out, reply_markup=language_menu_markup)
#     elif query.data.split(":")[1] == context.user_data.get("language"):
#         query.answer()
#     else:
#         query.answer()
#         context.user_data["language"] = query.data.split(":")[1]
#         logging.info("%s changed language to %s", context.user_data.get('name'), query.data.split(':')[1])

def set_language(update: Update, context: CallbackContext) -> (None):
    """Send a message when the command /set_language is issued."""
    query = update.callback_query
    lan = query.data.split(":")[1]
    if lan == context.user_data.get("language"):
        query.answer()
    else:
        query.answer()
        context.user_data["language"] = lan
        logging.info("%s changed language to %s", context.user_data.get('name'), lan)
    config.show_main_menu(update, context)


        # msg_out = f"Choose a language, current language is: " + context.user_data.get("language", "german")
        # query.edit_message_text(text=msg_out + "\nstart a new game with /new", reply_markup=language_menu_markup)

def start_game(update: Update, context: CallbackContext) -> (None):
    """Starts a new game"""
    query = update.callback_query
    if query != None:
        query.answer()
        update = query

    menu_msg = context.user_data.get("menu_msg")
    if menu_msg != None:
        menu_msg.delete()
    wordle = Wordle(context.user_data.get("language", "german"))
    context.user_data["wordle"] = wordle
    img = wordle.new_game(x=5, y=6)
    img.save(config.image_location(update, context))

    with open(config.image_location(update, context), "rb") as img:
        board_img_msg = update.message.reply_photo(img, reply_markup=give_up_markup)

    # todo delete picture and text message from previous game
    board_desc_msg = update.message.reply_text("Good luck!")

    context.user_data["board_img_msg"] = board_img_msg
    context.user_data["board_desc_msg"] = board_desc_msg
    logger.info(f"{context.user_data.get('name')} started a new game word: " + wordle.target_word)

def check_word(update: Update, context: CallbackContext) -> (None):
    logger.info(f"{update.message.from_user.first_name} guessed {update.message.text}")
    wordle = context.user_data["wordle"]

    # if wordle is None:
    #     update.message.repyl_text("You need to start a game first! you can use /new")
    #     return
    # if wordle.state == GameState.LOST:
    #     update.message.reply_text("You lost the game! Start a new one with /new")
    #     return
    if wordle.state == GameState.WON or wordle.state == GameState.LOST or wordle.state == GameState.INIT or wordle is None:
        config.show_main_menu(update, context)
        return

    img = wordle.try_word(update.message.text)
    if img is not None:
        img.save(config.image_location(update, context))
        img = open(config.image_location(update, context), "rb")

        context.user_data.get("board_img_msg").delete()
        context.user_data.get("board_desc_msg").delete()

        if wordle.state == GameState.WON:
            logger.info(f"{update.message.from_user.first_name} won the game")
            context.user_data["board_img_msg"] = update.message.reply_photo(img)
            update.message.reply_markdown_v2(f"You won, the word was: *{wordle.target_word}*")
            context.user_data["menu_msg"] = update.message.reply_text("What do you want to do now?", reply_markup=main_menu_markup)
        elif wordle.state == GameState.LOST:
            logger.info(f"{update.message.from_user.first_name} lost the game")
            context.user_data["board_img_msg"] = update.message.reply_photo(img)
            update.message.reply_markdown_v2(f"You lost, the word was: *{wordle.target_word}*")
            context.user_data["menu_msg"] = update.message.reply_text("What do you want to do now?", reply_markup=main_menu_markup)
        else:
            context.user_data["board_img_msg"] = update.message.reply_photo(img, reply_markup=give_up_markup)

        if wordle.state == GameState.PLAYING:
            context.user_data["board_desc_msg"] = update.message.reply_text("That looks good!")

        img.close()
    else:
        if wordle.state == GameState.PLAYING:
            context.user_data.get("board_desc_msg").edit_text("Try another word")


    # if wordle.state == GameState.WON:
    #     context.user_data.get("board_desc_msg").edit_text(f"You won, the word was: `{wordle.target_word}`")
    # if wordle.state == GameState.INIT:
    #     update.message.reply_text("You need to start a game first! you can use /new")

def help_command(update: Update, context: CallbackContext) -> (None):
    """Send a message when the command /help is issued."""
    context.user_data['menu_msg'] = update.message.reply_text("What do you want to do now?", reply_markup=main_menu_markup)

def give_up(update: Update, context: CallbackContext) -> (None):
    """Send a message when the command /give_up is issued."""
    query = update.callback_query
    query.answer()
    wordle = context.user_data["wordle"]
    img_msg = context.user_data.get("board_img_msg")
    # context.bot.edit_message_media(chat_id=query.message.chat_id, message_id=img_msg, reply_markup=None)
    img_msg.delete()
    with open(config.image_location(update, context), "rb") as img:
        query.message.reply_photo(img)
    context.user_data.get("board_desc_msg").delete()
    context.user_data['board_desc_msg'] = query.message.reply_markdown_v2(fr"You gave up, the word was: *{wordle.target_word}*")
    context.user_data["menu_msg"] = query.message.reply_text("What do you want to do now?", reply_markup=main_menu_markup)

    # query.message.reply_text(f"You gave up! The word was `{wordle.target_word}`\nStart a new game with /new")
    wordle.state = GameState.INIT
    logger.info(f"{context.user_data.get('name')} gave up")

def language_select(update: Update, context: CallbackContext) -> (None):
    """Send a message when the command /language is issued."""
    query = update.callback_query
    query.answer()
    config.show_language_menu(update, context)

def main() -> (None):
    """Start the bot."""
    load_dotenv()
    # Create the Updater and pass it your bot's token.
    updater = Updater(os.environ.get("API_TOKEN"), persistence=PicklePersistence(filename="wordle_bot_data"))

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("new", start_game))
    # dispatcher.add_handler(CommandHandler("language", change_language))
    dispatcher.add_handler(CallbackQueryHandler(set_language, pattern="set_lan:.*"))
    dispatcher.add_handler(CallbackQueryHandler(give_up, pattern="give_up"))
    dispatcher.add_handler(CallbackQueryHandler(start_game, pattern="new_game"))
    dispatcher.add_handler(CallbackQueryHandler(language_select, pattern="change_language"))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, check_word))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
