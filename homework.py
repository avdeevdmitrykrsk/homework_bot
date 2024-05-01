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
    '%(asctime)s, %(levelname)s, %(message)s, '
    '%(name)s, func: %(funcName)s, line: %(lineno)d'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter(format))
logger.addHandler(handler)

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
VALID_STATUS_CODE = HTTPStatus.OK


def check_tokens():
    """Проверка наличия переменных окружения."""
    logger.info('Начата проверка наличия токенов')
    CHECK_VARIABLES_LIST = (
        'PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID'
    )
    missing_tokens = [
        globals().get(var) for var in CHECK_VARIABLES_LIST
        if not globals().get(var)
    ]
    if missing_tokens:
        logger.critical('Не все переменные окружения найдены')
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
        logger.info('Данные API успешно получены')
    except requests.RequestException as error:
        raise ConnectionError(f'Ошибка соединения: {error}')
    if response.status_code != VALID_STATUS_CODE:
        raise ValueError(
            f'Ошибка ответа сервера - Status_code: {response.status_code}'
        )
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
    try:
        return response.get('homeworks')[HOMEWORK_NUMBER]
    except IndexError:
        raise ValueError('Список с домашками пуст')


def parse_status(homework):
    """Получаем нужную информацию из ответа."""
    logger.info('Попытка получения статуса домашки')
    if not homework.get('status'):
        raise ValueError('Ключ "status" в домашке не обнаружен.')
    if not homework.get('homework_name'):
        raise ValueError('Ключ "homework_name" в домашке не обнаружен.')

    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')

    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
            'Ошибка при получении ключа "status" из словаря вердиктов.'
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
    SENDED_MESSAGE = []
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 100000  # Иначе пустой список с домашками
    while True:
        try:
            message = parse_status(check_response(get_api_answer(timestamp)))
            if message not in SENDED_MESSAGE:
                send_message(bot, message)
                SENDED_MESSAGE.clear()
                SENDED_MESSAGE.append(message)
        except ConnectionError:
            logger.error(
                'Ошибка соединения: статус код отличный от 200: ',
                exc_info=True
            )
        except ApiTelegramException:
            logger.error('Ошибка отправки сообщения: ', exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message not in SENDED_MESSAGE:
                try:
                    send_message(bot, message)
                    SENDED_MESSAGE.clear()
                    SENDED_MESSAGE.append(message)
                    logger.error(
                        'Сообщение об ошибке успешно отправлено.',
                        exc_info=True
                    )
                except Exception:
                    logger.error(
                        'Ошибка при отправке сообщения пользователю. (main)',
                        exc_info=True
                    )
        finally:
            timestamp = int(time.time()) - 100000
            logger.info(
                f'Ожидание следующего запроса -- {RETRY_PERIOD} секунд.'
            )
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
