import os
import requests
from time import time, sleep


import logging
import telegram
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


load_dotenv()

TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
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
        os.environ['PRACTICUM_TOKEN']
        os.environ['TOKEN_TELEGRAM']
        os.environ['TELEGRAM_CHAT_ID']
    except KeyError as error:
        message = f'Отсутствует обязательная переменная окружения: {error}'
        logger.critical(message)
        print('Программа принудительно остановлена.')
        exit()


def send_message(bot, message):
    """Отправляет сообщение."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    message = f'сообщение было отправлено: {message}'
    logger.debug(message)


def get_api_answer(timestamp):
    """Проверяет ответ API."""
    timestamp = 0
    payload = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    if response.ok is True:
        return response.json()
    error = ('Эндпоинт '
             'https://practicum.yandex.ru/api/user_api/homework_statuses/111 '
             f'недоступен. Код ответа API: {response}')
    raise Exception(error)


def check_response(response):
    """Проверяет ответ API."""
    if response['homeworks'] and response['current_date']:
        return response['homeworks']
    error = 'отсутствуют ожидаемые ключи в ответе API'
    raise Exception(error)


def parse_status(homework):
    """Проверяет статус работы."""
    status = homework[0]['status']
    if status is not None and HOMEWORK_VERDICTS[status]:
        return ('Изменился статус проверки работы "{name}". '
                '{status}').format(name=homework[0]['homework_name'],
                                   status=HOMEWORK_VERDICTS[status])
    error = 'Нету ожидаемого ответа'
    raise Exception(error)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time())
    while True:
        check_tokens()
        sleep(600)
        try:
            api_answer = get_api_answer(timestamp)
            response_check = check_response(api_answer)
            status = parse_status(response_check)
            message = send_message(bot, status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


if __name__ == '__main__':
    main()
