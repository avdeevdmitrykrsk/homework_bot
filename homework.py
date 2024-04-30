import logging
import os
import sys
import time
from logging import StreamHandler

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (
    EmptyHomeworksListError, EmptyVariablesError, StatusCodeError, NoKeyError
)

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

# Loading variables from environment
load_dotenv()

# Access variables
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

HOMEWORK_NUMBER = 0
EMPTY_VALUE_HOMEWORKS = 0
VALID_STATUS_CODE = 200
STATUSES: list = []


def check_tokens():
    """Проверка наличия переменных окружения."""
    CHECK_VARIABLES_LIST = [
        PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    ]
    if all(CHECK_VARIABLES_LIST):
        logger.info('Все переменные окружения найдены.')
    else:
        logger.critical('Не все переменные окружения найдены.')
        raise EmptyVariablesError('Empty variable(s).')


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
        )
        if response.status_code != VALID_STATUS_CODE:
            logger.error('Cтатус код отличный от 200', exc_info=True)
            raise StatusCodeError(
                f'Ошибка ответа сервера - Status_code: {response.status_code}'
            )
        logger.info('Данные API успешно получены.')
        return response.json()
    except requests.RequestException as error:
        logger.error(error, exc_info=True)


def check_response(response):
    """Проверяем валидность данных."""
    if isinstance(response, dict):
        if 'homeworks' in response:
            if isinstance(response.get('homeworks'), list):
                if len(
                    response.get('homeworks')
                ) == EMPTY_VALUE_HOMEWORKS:
                    logger.debug('Нечего отображать')
                    raise EmptyHomeworksListError('Список с домашками пуст.')
                logger.info('Ответ от сервера проверен. Успех.')
                return response.get('homeworks')[HOMEWORK_NUMBER]
            raise TypeError('Список домашек не является типом list.')
        raise NoKeyError('В ответе сервера нет ключа homeworks.')
    raise TypeError('Ответ пришел не в виде словаря.')


def parse_status(homework):
    """Получаем нужную информацию из ответа."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status and homework_status in HOMEWORK_VERDICTS:
        if homework_name:
            if homework_status in STATUSES:
                logger.info('Статус домашки не изменился')
            else:
                STATUSES.clear()
                STATUSES.append(homework_status)
                logger.info(
                    (
                        f'Изменился статус проверки работы "{homework_name}". '
                        f'{verdict}'
                    )
                )
                return (
                    f'Изменился статус проверки работы "{homework_name}". '
                    f'{verdict}'
                )
        else:
            logger.debug('Отсутствует ключ "homework_name" в домашке')
            raise NoKeyError('Ошибка при получении ключа "homework_name".')
    else:
        logger.debug('Отсутствует ключ "status" в домашке')
        raise NoKeyError('Ошибка при получении ключа "status".')


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except EmptyVariablesError as error:
        logger.error(error, exc_info=True)
        sys.exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            # send_message(
            #     bot, parse_status(
            #         check_response(
            #             get_api_answer(timestamp)
            #         )
            #     )
            # )
            gai = get_api_answer(timestamp)
            cr = check_response(gai)
            ps = parse_status(cr)
            send_message(bot, ps)
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


if __name__ == '__main__':
    main()
