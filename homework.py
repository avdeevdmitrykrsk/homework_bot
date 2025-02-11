import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

# Logging settings.
format = (
    '%(levelname)s, func: %(funcName)s, line: %(lineno)d, '
    '%(name)s, %(asctime)s, %(message)s,'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(format))
logger.addHandler(handler)

# Loading variables from environment.
load_dotenv()

# Access variables.
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = os.getenv('RETRY_PERIOD')

# Number of "response" in homeworks list.
HOMEWORK_NUMBER = 0

# Connection settings.
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

# Connection retry period in seconds.

# Expected values of "response" status.
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия переменных окружения."""
    logger.info('Начата проверка наличия токенов')
    CHECK_VARIABLES_LIST = (
        'PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID'
    )
    missing_tokens = [
        var for var in CHECK_VARIABLES_LIST if not globals().get(var)
    ]
    if missing_tokens:
        logger.critical(
            f'Переменные окружения не найдены: {missing_tokens}.'
        )
        sys.exit(
            'Программа остановлена по причине: \nerror: empty variable(s).'
        )
    logger.info('Все переменные окружения найдены')


def send_message(bot, message):
    """Функция отправки сообщения в Telegram."""
    logger.info('Начата отправка сообщения пользователю')
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.debug('Сообщение пользователю успешно отправлено')


def get_api_answer(timestamp):
    """Получаем данные по API."""
    logger.info('Попытка получения данных по API')
    from_date = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=from_date
        )
    except requests.RequestException as error:
        raise ConnectionError(f'Ошибка соединения: {error}')
    if response.status_code != HTTPStatus.OK:
        raise ValueError(
            f'Ошибка ответа сервера - Status_code: {response.status_code}'
        )
    logger.info('Данные API успешно получены')
    return response.json()


def check_response(response):
    """Проверяем валидность данных."""
    logger.info('Начинаем проверку входящих данных')
    if not isinstance(response, dict):
        raise TypeError(
            (
                'Невалидный ответ сервера: '
                f'Входящий тип данных: {type(response)}. '
                'Ожидаемый тип данных: "dict".'
            )
        )
    if 'homeworks'not in response:
        raise KeyError('В ответе сервера нет ключа "homeworks".')

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError(
            (
                'Невалидный ответ сервера: '
                f'Входящий тип данных: {type(homeworks)}. '
                'Ожидаемый тип данных: "list".'
            )
        )
    logger.info('Входящие данные проверены. Успех')


def parse_status(response):
    """Получаем нужную информацию из ответа."""
    logger.info('Попытка получения статуса домашки')
    if 'status' not in response:
        raise KeyError('Ключ "status" в домашке не обнаружен.')
    if 'homework_name' not in response:
        raise KeyError('Ключ "homework_name" в домашке не обнаружен.')

    homework_status = response['status']
    homework_name = response['homework_name']

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Ошибка при получении ключа "{homework_status}" '
            'из словаря вердиктов.'
        )
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    message = (
        f'Изменился статус проверки работы "{homework_name}". '
        f'{verdict}'
    )
    logger.info(message)
    return message


def main():
    """Основная логика работы бота."""
    check_tokens()
    sended_message = ''
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks']
            if not homework:
                logger.debug('Список с домашками пуст.')
                continue
            message = parse_status(homework[HOMEWORK_NUMBER])
            if message not in sended_message:
                send_message(bot, message)
                sended_message = message
            else:
                logger.info(
                    'Отмена отправки сообщения, данное сообщение '
                    'уже было отправлено: \n'
                    f'"{message}"'
                )
            timestamp = response.get('current_date', int(time.time()))
        except ApiTelegramException:
            logger.error(
                'Ошибка при отправке сообщения пользователю. (main)',
                exc_info=True
            )
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message not in sended_message:
                try:
                    send_message(bot, message)
                    sended_message = message
                except ApiTelegramException:
                    logger.error(
                        'Ошибка при отправке сообщения пользователю. (main)',
                        exc_info=True
                    )
        finally:
            logger.info(
                f'Ожидание следующего запроса -- {RETRY_PERIOD} секунд.'
            )
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
