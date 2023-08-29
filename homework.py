from http import HTTPStatus
import logging
from logging.handlers import RotatingFileHandler
import os
import requests
import time
import sys

import telegram
from dotenv import load_dotenv

from exceptions import EmptyAnwserApiError, WrongAnwserServerError

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
stream_handler = logging.StreamHandler(stream=sys.stdout)
file_handler = RotatingFileHandler('homework.log',
                                   maxBytes=50000000,
                                   backupCount=5,
                                   encoding='utf-8'
                                   )
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    logger.debug('Началась проверка токенов.')
    tokens = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    return all(False for token in tokens if token is None)


def send_message(bot, message):
    """Отправляет сообщение."""
    logger.debug('Начался запуск функции send_message')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                         text=message)
        message = f'сообщение было отправлено: {message}'
        logger.info(message)
    except telegram.error.TelegramError as error:
        message = f'Сообщение не было отправлено {error}'
        logger.error(message)


def get_api_answer(timestamp):
    """Проверяет соединение API."""
    logger.debug('Началась проверка API соединения.')
    payload = {'from_date': timestamp}
    logger.debug(f'Начался запрос на адрес {ENDPOINT}, '
                 f'данные заголовка {HEADERS}, '
                 f'c параметрами {payload.get("from_date")}')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        return requests.RequestException('Ошибка соединения.')
    if response.status_code == HTTPStatus.OK:
        return response.json()
    raise WrongAnwserServerError('Ошибка доступа к серверу')


def check_response(response):
    """Проверяет ответ API."""
    logger.debug('Началась проверка ответа API')
    if not isinstance(response, dict):
        raise TypeError('Неправильный тип данных в API')
    if 'homeworks' not in response:
        raise EmptyAnwserApiError('Пустой ответ от сервера')
    homework = response.get('homeworks')
    if isinstance(homework, list):
        return homework
    raise TypeError('Неправильный тип данных внутри API')


def parse_status(homework):
    """Проверяет статус работы."""
    if 'status' not in homework:
        raise EmptyAnwserApiError('"status" - Нету ответа в API')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('В ответе пришел неправильный статус')
    verdict = HOMEWORK_VERDICTS[status]
    if 'homework_name' in homework:
        homework_name = homework['homework_name']
        message = f'Изменился статус проверки работы "{homework_name}" {verdict}'
        return message
    raise EmptyAnwserApiError('"homework_name" - Нету ответа в API')


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Отсутствует обязательная переменная окружения')
        logger.debug('Программа принудительно остановлена.')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_report = {
        'message': None
    }
    prev_report = {
        'message': None
    }
    while True:
        try:
            api_answer = get_api_answer(timestamp)
            timestamp = api_answer.get('current_date', timestamp)
            homeworks = check_response(api_answer)
            if homeworks:
                homework = homeworks[0]
                status = parse_status(homework)
                current_report.update({'message': status})
            current_report.update({'message': 'Нету нового статуса'})
            if current_report != prev_report:
                new_message = current_report.get('message')
                send_message(bot, new_message)
                prev_report = current_report.copy()
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            current_report.update({'message': message})
            if current_report != prev_report:
                message = current_report.get('message')
                send_message(bot, message)
                prev_report = current_report.copy()
            time.sleep(RETRY_PERIOD)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    main()
