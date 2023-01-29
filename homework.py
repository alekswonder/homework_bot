import os
import logging
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

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
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)


def check_tokens():
    """Checks availability of environment variables."""
    env_variables = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
                     'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
                     'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}
    for name, value in env_variables.items():
        if not value:
            message = f'{name} is not initialized or assigned with wrong value'
            logger.critical(message)
            raise ValueError(message)


def get_api_answer(timestamp):
    """Makes a request to the API and return JSON response."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        logging.error(error)
    else:
        return response.json()


def check_response(response):
    """Checks response API conformity to documentation."""
    keys_according_documentation = {'current_date': int(), 'homeworks': list()}
    for key, value in response.items():
        standard_type = type(keys_according_documentation.get(key))
        if key not in keys_according_documentation:
            message = (f'Responded API is not conformable to documentation: '
                       f'There is no such key as {key}')
            logger.error(message)
            raise UnboundLocalError(message)
        if not isinstance(value, standard_type):
            message = (f'Responded API is not conformable to documentation: '
                       f'Type of "{key}" is not equal to {standard_type}')
            logger.error(message)
            raise TypeError(message)


def parse_status(homework):
    """Extracts homework status, in case of success returns its verdict."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        message = f'Unexpected status {homework_status} from request'
        logging.error(message)
        raise ValueError(message)

    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Sends message in telegram chat by its id."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.debug(f'Bot sent message: "{message}"')


def main():
    """Main logic of bots work."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)

            if response.get('homeworks'):
                message = parse_status(response.get('homeworks')[0])
                send_message(bot, message)
            else:
                logger.debug('There is no new homework statuses in response')

            timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error)
            bot.send_message(TELEGRAM_CHAT_ID, message)


if __name__ == '__main__':
    main()
