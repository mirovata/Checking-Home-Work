import os
import sys
import requests
import time


import logging
import telegram
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('homework.log',
                              maxBytes=50000000,
                              backupCount=5,
                              encoding='utf-8'
                              )
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    try:
        if (PRACTICUM_TOKEN is not None
                or TELEGRAM_TOKEN is not None
                or TELEGRAM_CHAT_ID is not None):
            return
        raise TypeError
    except TypeError as error:
        message = f'Отсутствует обязательная переменная окружения: {error}'
        logger.critical(message)
        return TypeError


def send_message(bot, message):
    """Отправляет сообщение."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                         text=message)
        message = f'сообщение было отправлено: {message}'
        logger.debug(message)
    except telegram.error.TelegramError as error:
        message = f'Сообщение не было отправлено {error}'
        logger.error(message)


def get_api_answer(timestamp):
    """Проверяет ответ API."""
    payload = {'from_date': timestamp}
    error_endpoint = ('Эндпоинт '
                      'https://practicum.yandex.ru/api/'
                      'user_api/homework_statuses/111 '
                      'недоступен. Код ответа API: {}')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == 200:
            return response.json()
        raise Exception(error_endpoint.format(response.status_code))
    except requests.RequestException as error:
        message = f'Ошибка {error} в ответе API'
        logger.error(message)


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        logger.error('Неправильный тип данных в ответе response')
        raise TypeError
    if 'homeworks' not in response:
        logger.error('Нету ключа homeworks в ответе response')
        raise KeyError
    if not isinstance(response.get('homeworks'), list):
        logger.error('Неправильный тип данных в ответе response')
        raise TypeError
    for homework in response['homeworks']:
        return homework


def parse_status(homework):
    """Проверяет статус работы."""
    if 'status' not in homework:
        logger.error('Нету ключа status в homework')
        raise KeyError
    if 'homework_name' in homework:
        if HOMEWORK_VERDICTS.get(homework['status']):
            message = 'Изменился статус проверки работы "{name}" {ver}'.format(
                name=homework['homework_name'],
                ver=HOMEWORK_VERDICTS.get(homework['status']))
            return message
        logger.error('Нету ключа status в homework_verdicts')
        raise KeyError
    logger.error('Нету ключа homework_name в homework')
    raise KeyError


def main():
    """Основная логика работы бота."""
    if check_tokens() is TypeError:
        print('Программа принудительно остановлена.')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            api_answer = get_api_answer(timestamp)
            response_check = check_response(api_answer)
            status = parse_status(response_check)
            message = send_message(bot, status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(600)


if __name__ == '__main__':

    main()
