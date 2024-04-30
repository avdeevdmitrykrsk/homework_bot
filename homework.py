import os
import sys
import logging
import requests
import time
from dotenv import load_dotenv
from logging import StreamHandler
from pprint import pprint

import telegram
from telebot import TeleBot

from exceptions import EmptyHomeworksListError, EmptyVariables, StatusCodeError

# Logging settings.
format = '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(format))
logger.addHandler(handler)

logger.debug("A DEBUG message")
logger.info("An INFO message")
logger.warning("A WARNING message")
logger.error("An ERROR message")
logger.critical("A CRITICAL message")

load_dotenv()

PRACTICUM_TOKEN = None
TELEGRAM_TOKEN = None
TELEGRAM_CHAT_ID = None

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

STATUSES = []

CHECK_VARIABLES_LIST = [
    PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    RETRY_PERIOD, ENDPOINT, HEADERS, HOMEWORK_VERDICTS
]


def check_tokens():
    """Проверка наличия переменных окружения."""
    if all(CHECK_VARIABLES_LIST):
        logger.info('Все переменные окружения найдены.')
        return True
    logger.critical('Не все переменные окружения найдены.')
    return False


def send_message(bot, message):
    """Функция отправки сообщения в Telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Сообщение пользователю успешно отправлено.')
    except Exception:
        logger.error(
            'Ошибка при отправке сообщения пользователю. (send_message)',
            exc_info=True
        )


def get_api_answer(timestamp):
    """Получаем данные по API."""
    try:
        from_date = {'from_date': timestamp}
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=from_date
        ).json()
        logger.info('Данные API успешно получены.')
        return response
    except Exception as error:
        logger.error(error, exc_info=True)


def check_response(response):
    """Проверяем валидность данных."""
    try:
        if 'homeworks' in response:
            if isinstance(response, dict):
                if isinstance(response.get('homeworks'), list):
                    if len(response.get('homeworks')) == 0:
                        logger.debug('Нечего отображать')
                        raise EmptyHomeworksListError('Список с домашками пуст.')
                    logger.info('Ответ от сервера успешно получен.')
                    return response.get('homeworks')[0]
        logger.error('Невалидный ответ сервера.')
        raise TypeError('asd')
    except Exception as error:
        logger.error(error, exc_info=True)


def parse_status(homework):
    """Получаем нужную информацию из ответа."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status and homework_status in HOMEWORK_VERDICTS:
        if 'homework_name' in homework:
            if homework_status in STATUSES:
                logger.info('Статус домашки не изменился')
            else:
                STATUSES.clear()
                STATUSES.append(homework_status)
                logger.info(
                    f'Изменился статус проверки работы "{homework_name}". {verdict}'
                )
                return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    logger.debug('Отсутствует ключ "homework_name"')
    raise ValueError('asd')


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = TeleBot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())
        while True:
            try:
                send_message(
                    bot, parse_status(
                        check_response(
                            get_api_answer(timestamp)
                        )
                    )
                )
            except Exception as error:
                try:
                    message = f'Сбой в работе программы: {error}'
                    bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=message
                    )
                    logger.debug('Сообщение об ошибке успешно отправлено.')
                except Exception:
                    logger.error(
                        'Ошибка при отправке сообщения пользователю. (main)'
                    )
            finally:
                time.sleep(RETRY_PERIOD)
    else:
        logger.info('Программа остановлена.')
        sys.exit()


if __name__ == '__main__':
    main()
