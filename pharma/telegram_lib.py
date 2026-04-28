import pyqrcode
from django.conf import settings

from string import Template as tmp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from capsulae2.commons import get_or_none
from .telegram_bot import TelegramBot
from .telegram_messages import MESSAGES
from .telegram_models import TelegramUserChat


# --------------------------
#  UTILS
# ---------------------------
def tmp_parse(tmp_str, **kwargs):
    return tmp(tmp_str).substitute(**kwargs)

def get_update_data(update):
    chat_id = update.message.chat.id
    tg_user_chat = get_or_none(TelegramUserChat, chat_id, "telegram_chat_id")
    return chat_id, tg_user_chat

def get_message(key, params=None, lang="es"):
    try:
        message = MESSAGES[lang][key]
        if params:
            return tmp_parse(message, **params)
        return message
    except Exception as e:
        #logger.error(str(e))
        print(e)
        return ""

# ---------------------------
# Text Handler
# ---------------------------
def default_text_handler(bot, update):
    chat_id, tg_user_chat = get_update_data(update)
    bot.send_message(chat_id, get_message("no_text_allowed"))

# ---------------------------
#  Telegram GUI Actions
# ---------------------------
def send_identification_code(bot, update):
    chat_id, tg_user_chat = get_update_data(update)
    qr = pyqrcode.create(tg_user_chat.code)
    qrpath = "/pharma/templates/assets/codebars/"
    fullpath = "%s%s%s.svg" % (settings.BASE_DIR, qrpath, tg_user_chat.code)
    qr.png(fullpath, scale=4)
    message = get_message('welcome', {'code': tg_user_chat.code})
    bot.send_message(tg_user_chat.telegram_chat_id, message)
    bot.send_photo(chat_id=tg_user_chat.telegram_chat_id, photo=open(fullpath, "rb"))

def patient_treatments(bot, update):
    chat_id, tg_user_chat = get_update_data(update)

    tratamientos = tg_user_chat.patient.tratamientos.filter(activo=True)
    message = get_message('active_treatments')
    tline_tmp = get_message('treatment_line')
    for item in tratamientos:
        message += tmp_parse(tline_tmp, **{'med': item.name})
    try:
        bot.send_message(tg_user_chat.telegram_chat_id, message)
        return True
    except Exception as e:
        #logger.error(str(e))
        print(e)

    return None

def patient_register_confirm(bot, chat_id):
    keyboard = [
        [InlineKeyboardButton(get_message('register_confirm_btn'), callback_data='confirm')],
        [InlineKeyboardButton(get_message('register_reject_btn'), callback_data='reject')],

    ]
    reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    bot.send_message(chat_id, get_message("register_confirm_ask"), reply_markup=reply_markup)

def btns_actions(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    msg_id = query.message.message_id
    if query.data == 'confirm':
        bot.send_message(chat_id, get_message('register_confirmed'))
        tg_userchat = get_or_none(TelegramUserChat, chat_id, "telegram_chat_id")
        tg_userchat.confirmed = True
        tg_userchat.save()

    elif query.data == "reject":
        bot.send_message(chat_id, get_message("register_rejected"))

    bot.delete_message(chat_id, msg_id)

# ---------------------------
# Config
# ---------------------------
TG_BOT = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
TG_BOT.define_webhook(settings.TELEGRAM_BOT_WEBHOOK, None)
TG_BOT.start_idle()

TG_BOT.set_text_handler(default_text_handler)
# ---------------------------
# Commands
# ---------------------------
TG_BOT.add_command('start', send_identification_code)
TG_BOT.add_command('tratamientos', patient_treatments)
TG_BOT.add_command('confirm', patient_register_confirm)

TG_BOT.add_handler(CallbackQueryHandler(btns_actions))


