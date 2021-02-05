import requests
import telegram
import os
import logging
import zoneinfo

from time import sleep
from datetime import datetime
from urllib.parse import urlparse


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DVMN_API_TOKEN = os.getenv("DVMN_API_TOKEN")
CHAT_ID        = os.getenv("CHAT_ID")

USER_TIME_ZONE = os.getenv("USER_TIME_ZONE")
START_HOUR     = int(os.getenv("START_HOUR"))

LONG_POLLING_URL = "https://dvmn.org/api/long_polling/"
AUTHORIZATION_HEADERS = {
	"Authorization": f"Token {DVMN_API_TOKEN}"
}


## Messages ##
START_MESSAGE = "#### DVMN-бот запущен ####"

def get_telegram_report_message(work_title, lesson_url, is_negative):
	api_url_pr  = urlparse(LONG_POLLING_URL)
	lesson_path = urlparse(lesson_url).path
	
	url_pr = urlparse("")
	url_pr.scheme = api_url_pr.scheme
	url_pr.netloc = api_url_pr.netloc
	url_pr.path   = lesson_path

	url = url_pr.geturl()

	complite = f'✅["{work_title}"]({url}) - сдана✅'
	mistakes = f'🚫["{work_title}"]({url}) - с ошибкой🚫'

	return (mistakes if is_negative else complite)
## Messages end ##


def get_new_reviews(headers={}, params={}):
	response = requests.get(LONG_POLLING_URL, headers=headers, params=params)
	response.raise_for_status()
	return response.json()


def now_notification_time():
	now = datetime.now(zoneinfo.ZoneInfo(USER_TIME_ZONE))
	return (START_HOUR <= now.hour)


def start_long_polling_loop():
	timestamp = ""

	while now_notification_time():
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

		if reviews["status"]   == "timeout":
			timestamp = reviews["timestamp_to_request"]
		elif reviews["status"] == "found":
			attempts  = reviews["new_attempts"]

			while attempts:
				attempt = attempts[-1]

				try:
					bot.send_message(
						chat_id=CHAT_ID,
						text=get_telegram_report_message(
							attempt["lesson_title"],
							attempt["lesson_url"],
							attempt["is_negative"]
						),
						parse_mode=telegram.ParseMode.MARKDOWN,
						disable_web_page_preview=True
					)
				except telegram.error.TelegramError:
					raise
					sleep(60)
					continue
				
				attempts.pop(-1)

			timestamp = reviews["last_attempt_timestamp"]


bot = telegram.Bot(token=TELEGRAM_TOKEN)

logging.basicConfig(level=logging.INFO)
logging.info(START_MESSAGE)

start_long_polling_loop()
