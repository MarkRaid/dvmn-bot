import requests
import telegram
import os
import logging

from time import sleep
from urllib.parse import urlparse
from urllib.parse import urlunparse

LONG_POLLING_URL = "https://dvmn.org/api/long_polling/"

## Messages ##
START_MESSAGE = "#### DVMN-бот начал работать ####"

def get_telegram_report_message(work_title, lesson_url, is_negative):
	url_parts    = list(urlparse(LONG_POLLING_URL))
	url_parts[2] = urlparse(lesson_url).path
	
	url = urlunparse(url_parts)

	complite = f'✅[{work_title}]({url}) - сдана✅'
	mistakes = f'🚫[{work_title}]({url}) - с ошибкой🚫'

	return (mistakes if is_negative else complite)
## Messages end ##


def get_new_reviews(headers={}, params={}):
	response = requests.get(LONG_POLLING_URL, headers=headers, params=params)
	response.raise_for_status()
	return response.json()


def start_long_polling_loop(bot, DVMN_API_TOKEN, TELEGRAM_CHAT_ID):
	AUTHORIZATION_HEADERS = {
		"Authorization": f"Token {DVMN_API_TOKEN}"
	}
	timestamp = ""

	while True:
		try:
			try:
				reviews = get_new_reviews(
					headers=AUTHORIZATION_HEADERS,
					params={"timestamp": timestamp},
				)
			except (
				requests.exceptions.ConnectionError,
				requests.exceptions.ReadTimeout
			):
				sleep(60)
				continue

			resp_status = reviews["status"]

			if resp_status   == "timeout":
				timestamp = reviews["timestamp_to_request"]
			elif resp_status == "found":
				attempts  = reviews["new_attempts"]

				send_fails_count = 0

				while attempts:
					attempt = attempts[-1]

					try:
						bot.send_message(
							chat_id=TELEGRAM_CHAT_ID,
							text=get_telegram_report_message(
								attempt["lesson_title"],
								attempt["lesson_url"],
								attempt["is_negative"]
							),
							parse_mode=telegram.ParseMode.MARKDOWN,
							disable_web_page_preview=True
						)
					except telegram.error.TelegramError:
						if 10 <= send_fails_count: raise

						send_fails_count += 1
						sleep(60)
						continue
					else:
						attempts.pop(-1)

				timestamp = reviews["last_attempt_timestamp"]
			else:
				raise Exception(f"Неизвестный статус ответа сервера: {resp_status}")
		except:
	   		logging.exception("Бот упал с ошибкой:")


if __name__ == "__main__":
	TELEGRAM_BOT_TOKEN	= os.environ["TELEGRAM_BOT_TOKEN"]
	TELEGRAM_CHAT_ID 	= os.environ["TELEGRAM_CHAT_ID"]
	TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
	DVMN_API_TOKEN 		= os.environ["DVMN_API_TOKEN"]

	bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

	class TelegramHandler(logging.Handler):
		def emit(self, record):
			log_entry = self.format(record)
			bot.send_message(TELEGRAM_CHAT_ID, log_entry)

	logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)
	logger.addHandler(TelegramHandler())

	logger.info(START_MESSAGE)

	start_long_polling_loop(
		bot,
		DVMN_API_TOKEN,
		TELEGRAM_CHANNEL_ID
	)
