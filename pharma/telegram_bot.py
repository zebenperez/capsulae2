import logging

from datetime import datetime as dt
from queue import Queue

from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, Dispatcher
from telegram import Bot, ParseMode
from threading import Thread

logger = logging.getLogger(__name__)

UNKNOWN_RESPONSE_TEXT = "I'm sorry I don't  understand. Could you repeat please?"

class TelegramBot(Bot):

    @staticmethod
    def get_message_user(updater):
        return updater.messge, updater.message.from_user

    @staticmethod
    def sender_is_bot(updater):
        return updater.message.from_user.is_bot

    def __init__(self, token, unknown_response_text=UNKNOWN_RESPONSE_TEXT):
        self._token = token
        self._unknown_response_text = unknown_response_text
        self._updater = Updater(token=token)
        # self._updater.dispatcher.add_handler(MessageHandler(Filters.command, self.command_parser))
        self._reg_commands = {}
        self._reg_commands_help = {}

        if not self._token:
            logger.critical("No se ha podido encontrar un token válido para este bot")
        else:
            super(TelegramBot, self).__init__(self._token)

    # ------------------------
    # Define el webhook al que telegram enviará sus mensajes
    # ------------------------
    def define_webhook(self, webhook_url, cert_path):
        cert = None
        if cert_path:
            cert = open(cert_path, 'rb')
        self.set_webhook(webhook_url=webhook_url, certificate=cert)
        # self._updater.idle()

    def start_idle(self):
        self._update_queue = Queue()
        self._dispatcher = Dispatcher(self, None, workers=0)
        self._dispatcher.add_handler(MessageHandler(Filters.command, self.command_parser))

        # t = Thread(target=self._dispatcher.start, name="dispatcher")
        # t.start()

        # return self._dispatcher

    def command_help(self):
        return self._reg_commands_help

    def process_update(self, update):
        self._dispatcher.process_update(update)

    # --------------------------
    # Envia un mensaje exclusivamente al chat registrado como "admin_id"
    # ---------------------------
    def send_to_admin(self, text):
        self._send_message(self._admin_id, text, True)

    # --------------------------
    # permite enviar un mensaje al chat pasado como parametro
    # ---------------------------
    def send_message(self, chat_id, text, notification=True, parse_mode=ParseMode.HTML, link_preview=True, **kwargs):
        disable_not = not notification
        link_preview = not link_preview
        try:
            super(TelegramBot, self).send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_not,
                diable_web_page_preview=link_preview,
                **kwargs)
            return True
        except Exception as e:
            print(e)
            return False

    # ---------------------------
    # Permite agregar acciones y reaccionar a ellas
    # ---------------------------
    def add_command(self, command, handler, kwargs={}):
        if command not in self._reg_commands.keys():
            self._reg_commands[command] = handler
            self._reg_commands_help[command] = kwargs.get("help", "")

    def unknown_command(self, chat_id):
        self.send_message(chat_id, self._unknown_response_text, True)

    # Version del command parser para utilizar con el dispatcher de python telegrambot
    def command_parser(self, _, update):
        try:
            msg = update.message.text.split(" ")
            command = msg[0].replace("/", "")
            args = msg[1:]
            handler = self._reg_commands.get(command, None)
            if handler:
                if args:
                    handler(self, update, args)
                else:
                    handler(self, update)
            else:
                self.unknown_command()
        except Exception as e:
            logger.error("[command-err] %s" % str(e))

    def reply_text(self, message, reply_markup, update):
        update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    # ---------------------------
    # Permite estalecer el metodo encargado de reaccionar a las entradas de texto
    # ---------------------------

    def set_text_handler(self, handler):
        thandler = MessageHandler(Filters.text, handler)
        self._dispatcher.add_handler(thandler)

    # -----------------------
    # Permite establecer el metodo encargado de manejar las localizaciones
    # ----------------------
    def set_location_handler(self, handler):
        lhandler = MessageHandler(Filters.location, handler)
        self._dispatcher.add_handler(lhandler)

    def add_handler(self, handler_class):
        self._dispatcher.add_handler(handler_class)

