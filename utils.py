import logging
import requests
import time
from datetime import datetime, timedelta, timezone


def beijing_time(*args, **kwargs):
    bj_time = datetime.utcnow() + timedelta(hours=8)
    return bj_time.timetuple()


def time_now():
    now = (
        datetime.utcnow()
        .replace(tzinfo=timezone.utc)
        .astimezone(timezone(timedelta(hours=8)))
    )
    return now


def request(*args, timeout=3, **kwargs):
    is_retry = True
    count = 0
    max_retries = 15
    sleep_seconds = 0.5
    # proxy = {'http': 'http://127.0.0.1:8866', 'https': 'http://127.0.0.1:8866'}
    # requests.packages.urllib3.disable_warnings()
    while is_retry and count <= max_retries:
        try:
            s = requests.Session()
            response = s.request(*args, timeout=timeout, **kwargs)
            # response = s.request(
            #     *args, **kwargs, timeout=2, proxies=proxy, verify=False
            # )
            is_retry = False
        except Exception as e:
            if count == max_retries:
                raise e
            log.error(f'Request failed: {e}')
            count += 1
            log.info(
                f'Trying to reconnect in {sleep_seconds} seconds ({count}/{max_retries})...'
            )
            time.sleep(sleep_seconds)
        else:
            return response


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logging.Formatter.converter = beijing_time
log = logging.getLogger()

start_time = datetime.combine(
    time_now().date(), datetime.strptime("07:00:00", "%H:%M:%S").time()
).replace(tzinfo=timezone(timedelta(hours=8)))

stop_time = datetime.combine(
    time_now().date(), datetime.strptime("21:00:00", "%H:%M:%S").time()
).replace(tzinfo=timezone(timedelta(hours=8)))
