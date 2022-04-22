import json
import os
import ruamel.yaml
import logging
from utils import log, request

yaml = ruamel.yaml.YAML()


class Config(object):
    def __init__(self):
        self.config: dict = {}

        self.auth: dict = {}
        self.court_id: str = ''
        self.court_list: list = []
        self.notify: dict = {}
        self.resources: dict = {}

        self.project_path = os.path.dirname(__file__)
        self.config_file = os.path.join(self.project_path, 'config.yaml')

        self.load_config()  # 加载配置
        self.load_resources()

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
        self.court_id = self.config.get('court_id')
        self.court_list = self.config.get('court_list')
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


config = Config()

# 设置日志等级
if config.config.get('log_level'):
    if config.config.get('log_level').lower() == 'debug':
        log.setLevel(logging.DEBUG)
