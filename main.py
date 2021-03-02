import os
import logging

from time import sleep

import requests
import telegram

from bot_logger import TelegramHandler


DVMN_URL = "https://dvmn.org"
LONG_POLLING_URL = DVMN_URL + "/api/long_polling/"

logger = logging.getLogger()


# Messages
def get_start_message():
	return "#### DVMN-бот начал работать ####"


def get_telegram_report_message(work_title, lesson_url, is_negative):
	url = DVMN_URL + lesson_url

	complite = f'✅[{work_title}]({url}) - сдана✅'
	mistakes = f'🚫[{work_title}]({url}) - с ошибкой🚫'

	return (mistakes if is_negative else complite)
# Messages end


def get_new_reviews(headers={}, params={}):
	response = requests.get(LONG_POLLING_URL, headers=headers, params=params)
	response.raise_for_status()
	return response.json()


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
				sleep(60)
				continue
			except requests.exceptions.ReadTimeout:
				continue

			resp_status = reviews["status"]

			if resp_status == "timeout":
				timestamp = reviews["timestamp_to_request"]
			elif resp_status == "found":
				for attempt in reversed(reviews["new_attempts"]):
					for _ in range(10):
						try:
							bot.send_message(
								chat_id=telegram_chat_id,
								text=get_telegram_report_message(
									attempt["lesson_title"],
									attempt["lesson_url"],
									attempt["is_negative"]
								),
								parse_mode=telegram.ParseMode.MARKDOWN,
								disable_web_page_preview=True
							)
							break
						except telegram.error.TelegramError:
							sleep(60)
					else:
						raise

				timestamp = reviews["last_attempt_timestamp"]
			else:
				raise Exception(f"Неизвестный статус ответа сервера: {resp_status}")
		except:
			logging.exception("Бот упал с ошибкой:")


if __name__ == "__main__":
	telegram_bot_token	= os.environ["TELEGRAM_BOT_TOKEN"]
	telegram_chat_id 	= os.environ["TELEGRAM_CHAT_ID"]
	telegram_channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
	dvmn_api_token 		= os.environ["DVMN_API_TOKEN"]

	bot = telegram.Bot(token=telegram_bot_token)

	logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
	logger.setLevel(logging.INFO)
	logger.addHandler(TelegramHandler(bot, telegram_chat_id))

	logger.info(get_start_message())

	start_long_polling_loop(
		bot,
		dvmn_api_token,
		telegram_channel_id
	)
