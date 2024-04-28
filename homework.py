import requests
from datetime import time
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = ...
TELEGRAM_TOKEN = ...
TELEGRAM_CHAT_ID = ...

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

CHECK_VARIABLES_LIST = [
    PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    RETRY_PERIOD, ENDPOINT, HEADERS, HOMEWORK_VERDICTS
]


def check_tokens():
    if all(CHECK_VARIABLES_LIST):
        return True
    return False

def send_message(bot, message):
    ...


def get_api_answer(timestamp):
    from_date = {'from_date': timestamp}
    check_response(
        requests.get(
            ENDPOINT, params=from_date
        ).json()
    )


def check_response(response):
    if response.status_code == 200:
        parse_status(response.get('homework')[0])


def parse_status(homework):
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    if check_tokens():

        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())
        get_api_answer(timestamp)

        while True:
            try:

                ...

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                ...
            ...


if __name__ == '__main__':
    main()
