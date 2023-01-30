import json
import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

MESSAGE_FOR_CHECK_TOKENS = ('{name} is not initialized or'
                            ' assigned with wrong value')
MESSAGE_FOR_GET_API_ANSWER_ACTION = (
    'Something wrong with your {action}!\n'
    'URL:{endpoint},\n'
    'HEADERS: {headers},\n'
    'REQUEST PARAMETERS: {request_parameters},\n'
    'ERROR: {error}\n')
MESSAGE_FOR_GET_API_ANSWER_JSON = 'JSON is not valid {error}'
MESSAGE_FOR_CHECK_RESPONSE_INSTANCE_OF_DICT = (
    "Received response has wrong type that "
    "{response_type} does not match <class 'dict'>")
MESSAGE_FOR_CHECK_RESPONSE_KEY_IN_API_DOC = (
    'Responded API is not conformable to documentation: '
    'There is no such key as {key}')
MESSAGE_FOR_CHECK_RESPONSE_TYPES_ARE_MATCHED = (
    'Responded API is not conformable to documentation: '
    'Type of "{key}" is not equal to {standard_type}')
MESSAGE_FOR_PARSE_STATUS_HW_NAME_IN_ARGUMENT_DICT = (
    'There is no key "homework_name" in homework')
MESSAGE_FOR_PARSE_STATUS_UNEXPECTED = (
    'Unexpected status {homework_status} from request')
MESSAGE_FOR_PARSE_STATUS_RETURN_VALUE = ('Изменился статус проверки работы '
                                         '"{homework_name}". {verdict}')
MESSAGE_FOR_SEND_MESSAGE_SUCCESS = 'Bot sent message: "{message}"'
MESSAGE_FOR_SEND_MESSAGE_ERROR = ('There is an error while you '
                                  'trying send a message via bot: {error}')
MESSAGE_FOR_MAIN_IF_NO_NEW_STATUS = (
    'There is no new homework statuses in response')
MESSAGE_FOR_MAIN_ERROR = 'Сбой в работе программы: {error}'

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
stream_handler = logging.StreamHandler(sys.stdout)
rotating_file_handler = RotatingFileHandler(__file__ + '.log',
                                            maxBytes=50000000,
                                            backupCount=5)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
stream_handler.setFormatter(formatter)
rotating_file_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.addHandler(rotating_file_handler)


def check_tokens():
    """Checks availability of environment variables."""
    env_variables = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
                     'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
                     'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}

    for name, value in env_variables.items():
        if not value:
            message = MESSAGE_FOR_CHECK_TOKENS.format(name=name)
            logger.critical(message)
            raise ValueError(message)


def get_api_answer(timestamp):
    """Makes a request to the API and return JSON response."""
    response = None
    request_parameters = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=request_parameters
        )
    except requests.RequestException as error:
        message = MESSAGE_FOR_GET_API_ANSWER_ACTION.format(
            action='request', endpoint=ENDPOINT, headers=HEADERS,
            request_parameters=request_parameters, error=error)
        logger.error(message)

    if response.status_code != HTTPStatus.OK:
        message = MESSAGE_FOR_GET_API_ANSWER_ACTION.format(
            action='response', endpoint=ENDPOINT, headers=HEADERS,
            request_parameters=request_parameters, error=response.status_code)
        raise Exception(message)

    try:
        result = response.json()
    except json.decoder.JSONDecodeError as error:
        message = MESSAGE_FOR_GET_API_ANSWER_JSON.format(error=error)
        logger.error(message)
        raise json.decoder.JSONDecodeError(message)

    return result


def check_response(response):
    """Checks response API conformity to documentation."""
    keys_according_documentation = {'current_date': int(), 'homeworks': list()}

    if not isinstance(response, type(dict())):
        message = MESSAGE_FOR_CHECK_RESPONSE_INSTANCE_OF_DICT.format(
            response_type=type(response))
        logger.error(message)
        raise TypeError(message)

    for key in keys_according_documentation.keys():
        if key not in response.keys():
            message = MESSAGE_FOR_CHECK_RESPONSE_KEY_IN_API_DOC.format(key=key)
            logger.error(message)
            raise Exception(message)

    for key, value in response.items():
        standard_type = type(keys_according_documentation.get(key))
        if not isinstance(value, standard_type):
            message = MESSAGE_FOR_CHECK_RESPONSE_TYPES_ARE_MATCHED.format(
                key=key, standard_type=standard_type)
            logger.error(message)
            raise TypeError(message)


def parse_status(homework):
    """Extracts homework status, in case of success returns its verdict."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if 'homework_name' not in homework:
        message = MESSAGE_FOR_PARSE_STATUS_HW_NAME_IN_ARGUMENT_DICT
        logger.error(message)
        raise Exception(message)

    if homework_status not in HOMEWORK_VERDICTS:
        message = MESSAGE_FOR_PARSE_STATUS_UNEXPECTED.format(
            homework_status=homework_status)
        logger.error(message)
        raise KeyError(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return MESSAGE_FOR_PARSE_STATUS_RETURN_VALUE.format(
        homework_name=homework_name, verdict=verdict)


def send_message(bot, message):
    """Sends message in telegram chat by its id."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(MESSAGE_FOR_SEND_MESSAGE_SUCCESS.format(message=message))
    except Exception as error:
        logger.error(MESSAGE_FOR_SEND_MESSAGE_ERROR.format(error=error))


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
                logger.debug(MESSAGE_FOR_MAIN_IF_NO_NEW_STATUS)

            timestamp = response.get('current_date')
        except Exception as error:
            message = MESSAGE_FOR_MAIN_ERROR.format(error=error)
            logger.error(message)
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
