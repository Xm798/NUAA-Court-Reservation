import json
import os
import ruamel.yaml
import logging
from utils import log, request, time_now

yaml = ruamel.yaml.YAML()


class Config(object):
    def __init__(self):
        self.config: dict = {}
        self.resources: dict = {}

        self.auth: dict = {}
        self.court_id: str = ''
        self.courts_list: list = []
        self.courts_list_readable: list = []
        self.notify: dict = {}

        self.project_path = os.path.dirname(__file__)
        self.config_file = os.path.join(self.project_path, 'config.yaml')

        self.load_config()  # 加载配置
        self.load_resources()   # 加载资源
        self.parse_courts()  # 解析场地列表

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
                log.error('配置文件加载失败！')
                log.error(e)
                exit()
        else:
            log.error('配置文件不存在！')
            exit()

        self.auth = self.config.get('auth')
        self.court_id = str(self.config.get('court_id'))
        self.notify = self.config.get('notify')
        os.environ['COURT_RESERVATION_OCR_API'] = self.config.get('ocr_api')

    def load_resources(self):
        resources_file = self.config.get('resources_file')
        if resources_file:
            log.info('在线加载资源列表...')
            try:
                r = request('get', resources_file)
                self.resources = r.json()
            except Exception as e:
                log.error('在线加载资源列表失败！')
                log.error(e)
            else:
                log.info('在线加载资源列表成功！')
                return
        resources_file = os.path.join(self.project_path, 'resources.json')

        with open(resources_file, 'r', encoding='utf-8') as f:
            log.info('从本地加载资源列表...')
            self.resources = json.load(f)

    def parse_courts(self):
        date = time_now().strftime("%Y-%m-%d")
        courts_list_input = self.config.get('courts_list')
        for i, courts in enumerate(courts_list_input):
            for j, court in enumerate((courts['courts'])):
                self.courts_list.append({
                    'date': date,
                    'period': self.resources['resource_list'][self.court_id]['time_list'][courts['time']],
                    'sub_resource_id': self.resources['resource_list'][self.court_id]['court_list'][courts['time']][str(court)+"号"]
                })
                self.courts_list_readable.append({
                    'date': date,
                    'period': courts['time'],
                    'sub_resource_id': str(court)+"号"
                })


config = Config()

# 设置日志等级
if config.config.get('log_level'):
    if config.config.get('log_level').lower() == 'debug':
        log.setLevel(logging.DEBUG)
