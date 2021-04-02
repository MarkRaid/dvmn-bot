import os
import logging
import time

import telegram
import requests

from retrying import retry

from bot_logger import TelegramHandler


DVMN_URL = "https://dvmn.org"
LONG_POLLING_URL = f'{DVMN_URL}/api/long_polling/'

logger = logging.getLogger()


# Messages
start_message = "# DVMN-бот начал работать #"


def telegram_report_message(work_title, lesson_url, is_negative):
    url = f'{DVMN_URL}{lesson_url}'
    mdLink = f'[{work_title}]({url})'

    complite = f'✅{mdLink} - сдана✅'
    mistakes = f'🚫{mdLink} - с ошибкой🚫'

    return (
        mistakes
        if is_negative
        else complite
    )
# Messages end


def get_new_reviews(headers={}, params={}):
    response = requests.get(LONG_POLLING_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def retry_if_telegram_error(exception):
    return isinstance(exception, telegram.error.TelegramError)


@retry(
    stop_max_attempt_number=20,
    wait_fixed=1000,
    retry_on_exception=retry_if_telegram_error
)
def send_message(message, bot, telegram_chat_id):
    bot.send_message(
        chat_id=telegram_chat_id,
        text=message,
        parse_mode=telegram.ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


def start_long_polling_loop(bot, dvmn_api_token, telegram_chat_id):
    timestamp = ""

    while True:
        try:
            try:
                reviews = get_new_reviews(
                    headers={"Authorization": f"Token {dvmn_api_token}"},
                    params={"timestamp": timestamp},
                )
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
            ):
                time.sleep(60)
                continue
            except requests.exceptions.ReadTimeout:
                continue

            resp_status = reviews["status"]

            if resp_status != "found":
                timestamp = reviews["timestamp_to_request"]
                continue

            for attempt in reversed(reviews["new_attempts"]):
                message = telegram_report_message(
                    attempt["lesson_title"],
                    attempt["lesson_url"],
                    attempt["is_negative"]
                )

                send_message(message, bot, telegram_chat_id)

            timestamp = reviews["last_attempt_timestamp"]
        except:
            logging.exception("Бот упал с ошибкой:")


if __name__ == "__main__":
    telegram_channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
    dvmn_api_token = os.environ["DVMN_API_TOKEN"]

    bot = telegram.Bot(token=telegram_bot_token)

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramHandler(bot, telegram_chat_id))

    logger.info(start_message)

    start_long_polling_loop(
        bot,
        dvmn_api_token,
        telegram_channel_id
    )
