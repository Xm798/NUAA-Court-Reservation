import os
import logging
import requests
import time
import ruamel.yaml
from datetime import datetime, timedelta, timezone

yaml = ruamel.yaml.YAML()


class Config(object):
    def __init__(self):
        self.config: dict = {}

        self.auth: dict = {}
        self.court_id: str = ''
        self.court_list: list = []
        self.notify: dict = {}

        project_path = os.path.dirname(__file__)
        self.config_file = os.path.join(project_path, 'config.yaml')
        self.load_config()  # 加载配置

    def __getitem__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                f = open(self.config_file, 'r', encoding='utf-8')
                data = f.read()
                self.config = yaml.load(data)
            except Exception as e:
                log.error('读取配置文件失败！')
                log.error(e)
                exit()
        else:
            log.error('配置文件不存在！')
            exit()

        self.auth = self.config.get('auth')
        self.court_id = self.config.get('court_id')
        self.court_list = self.config.get('court_list')
        self.notify = self.config.get('notify')
        os.environ['COURT_RESERVATION_OCR_API'] = self.config.get('ocr_api')

    # def dump_config(self):
    #     try:
    #         self.config['auth'].update(self.auth)
    #         with open(self.config_file, 'w', encoding='utf-8') as f:
    #             yaml.dump(self.config, f)
    #
    #     except Exception as e:
    #         log.error('写入配置文件失败！')
    #         log.debug(e)
    #     else:
    #         log.info('配置文件更新成功！')


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


def request(*args, **kwargs):
    is_retry = True
    count = 0
    max_retries = 20
    sleep_seconds = 0.5
    # proxy = {'http': 'http://127.0.0.1:8866', 'https': 'http://127.0.0.1:8866'}
    requests.packages.urllib3.disable_warnings()
    while is_retry and count <= max_retries:
        try:
            s = requests.Session()
            response = s.request(*args, **kwargs, timeout=1)
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


logging.Formatter.converter = beijing_time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

log = logging

start_time = datetime.combine(
    time_now().date(), datetime.strptime("07:00:00", "%H:%M:%S").time()
).replace(tzinfo=timezone(timedelta(hours=8)))

stop_time = datetime.combine(
    time_now().date(), datetime.strptime("21:00:00", "%H:%M:%S").time()
).replace(tzinfo=timezone(timedelta(hours=8)))

config = Config()
