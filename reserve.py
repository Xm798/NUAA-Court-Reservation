# encoding=utf-8
import json
import logging
import re
import time
import requests
import toml
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
from notify import Notify

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

log = logging


def request(*args, **kwargs):
    is_retry = True
    count = 0
    max_retries = 3
    sleep_seconds = 1
    while is_retry and count <= max_retries:
        try:
            s = requests.Session()
            response = s.request(*args, **kwargs, timeout=1)
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


class NUAA(object):
    def __init__(self, user):
        self.auth: dict = user['auth']
        self.cookie_ehall: dict = {}
        self.name: str = ''
        self.court_id: int = user['court_id']  # 场地类型
        self.court_list: list = user['clout_list']  # 场地列表
        self.notify_conf: dict = user['notify']
        self.push_content: list = []

    @staticmethod
    def time_check():
        now = (
            datetime.utcnow()
            .replace(tzinfo=timezone.utc)
            .astimezone(timezone(timedelta(hours=8)))
        )
        start_time = datetime.combine(
            now.date(), datetime.strptime("07:00:01", "%H:%M:%S").time()
        ).replace(tzinfo=timezone(timedelta(hours=8)))
        if now < start_time:
            delta = float((start_time - now).total_seconds())
            log.info(f'还未到开始时间，等待{delta}秒')
            time.sleep(delta)

    def get_ehall_cookie(self):
        try:
            headers = {
                'Host': 'ehall3.nuaa.edu.cn',
                'Accept-Encoding': 'gzip, deflate, br',
                'deviceType': 'ios',
                'refresh_token': self.auth.get('refresh_token'),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
                'token': self.auth.get('access_token'),
                'access_token': self.auth.get('access_token'),
                'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            }
            response = request(
                "GET",
                'https://ehall3.nuaa.edu.cn/api/login/nuaa-app-login?redirect=https://m.nuaa.edu.cn/site/applicationSquare/index?sid=7',
                headers=headers,
                allow_redirects=False,
            )
        except Exception as e:
            log.error('登录预约系统失败，未知原因，请查阅 debug 日志')
            self.push_content.append('登录预约系统失败，未知原因，请查阅 debug 日志')
            log.debug(e)
            return False
        else:
            vjuid = re.search(
                r'(?<=(vjuid=))[a-zA-Z0-9]+', response.headers['Set-Cookie']
            ).group(0)
            vjvd = re.search(
                r'(?<=(vjvd=))[a-zA-Z0-9]+', response.headers['Set-Cookie']
            ).group(0)
            vt = re.search(
                r'(?<=(vt=))[a-zA-Z0-9]+', response.headers['Set-Cookie']
            ).group(0)
            phpsessid = re.search(
                r'(?<=(PHPSESSID=))[a-zA-Z0-9]+', response.headers['Set-Cookie']
            ).group(0)
            self.cookie_ehall = {
                'PHPSESSID': phpsessid,
                'vjuid': vjuid,
                'vjvd': vjvd,
                'vt': vt,
            }
            if vjuid and vjvd and vt and phpsessid:
                log.info('获取预约系统鉴权信息成功')
                return True
            else:
                log.error('获取预约系统鉴权信息失败，请查阅 debug 日志')
                self.push_content.append('获取预约系统鉴权信息失败，请查阅 debug 日志')
                log.debug(response.headers)
                return False

    def get_name(self):
        try:
            headers = {
                'Host': 'ehall3.nuaa.edu.cn',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
                'Referer': 'https://ehall3.nuaa.edu.cn/v2/reserve/m_myReserve',
                'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
                'X-Requested-With': 'XMLHttpRequest',
            }
            response = request(
                'get',
                'https://ehall3.nuaa.edu.cn/site/user/get-name',
                cookies=self.cookie_ehall,
                headers=headers,
            )
            response.encoding = 'utf-8'
            r = response.json()
            name = r['d'].get('name')
            number = r['d'].get('number')
            self.push_content.append(f'账号：{name} {number}')
        except Exception as e:
            log.info('姓名获取失败')
            log.debug(e)

    def reserve(self, court_data):
        try:
            body = {
                'resource_id': self.court_id,
                'code': "",
                'remarks': "",
                'deduct_num': "",
                'data': f'[{json.dumps(court_data)}]',
            }
            body = urlencode(body)
            headers = {
                'Host': 'ehall3.nuaa.edu.cn',
                'Accept': 'application/json, text/plain, */*',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://ehall3.nuaa.edu.cn',
                'Referer': 'https://ehall3.nuaa.edu.cn/v2/reserve/m_reserveDetail?id=19',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
            }
            response = request(
                'post',
                'https://ehall3.nuaa.edu.cn/site/reservation/launch',
                data=body,
                cookies=self.cookie_ehall,
                headers=headers,
            )
            response.encoding = 'utf-8'
        except Exception as e:
            log.error('提交预约失败！详情见 debug 日志。')
            self.push_content.append('提交预约失败！详情见 debug 日志。')
            log.debug(e)
        else:
            r = response.json()
            fail_info = f"id为{court_data['sub_resource_id']}，时间为{court_data['period']}的场地预约失败，原因为{r['m']}"
            if r['m'] == '操作成功':
                log.info(
                    f"id为{court_data['sub_resource_id']}，时间为{court_data['period']}的场地预约成功"
                )
                self.push_content.append(
                    f"id为{court_data['sub_resource_id']}，时间为{court_data['period']}的场地预约成功"
                )
                return 1
            elif r['m'] == "不在服务时间":
                log.info(fail_info)
                self.push_content.append(fail_info)
                return 0
            else:  # r['m'] == '预约日期已约满' or r['m'] == '预约日期已被禁用':
                log.info(fail_info)
                self.push_content.append(fail_info)
                return -1

    def launch_reserve(self, court):
        i = self.reserve(court)
        while i == 0:
            time.sleep(1)
            i = self.reserve(court)
        return i

    def run(self):
        if not self.auth:
            log.error('该账号配置错误，退出...')
            return
        log.info('STEP2: 获取预约系统鉴权信息...')
        if not self.get_ehall_cookie():
            return
        log.info('STEP3: 获取用户基本信息...')
        self.get_name()
        self.time_check()
        log.info('STEP4: 提交预约申请...')
        for court in self.court_list:
            result = self.launch_reserve(court)
            if result == 1:  # 预约成功
                return True
            elif result == -1:  # 预约失败，换个场地
                time.sleep(0.5)  # 稍微歇会
                # continue
        return False

    def push(self, status):
        notify = Notify(self.notify_conf)
        title = '体育场地预约成功！' if status else '体育场地预约失败！'
        time_now = (
            datetime.utcnow()
            .replace(tzinfo=timezone.utc)
            .astimezone(timezone(timedelta(hours=8)))
            .strftime("%Y-%m-%d %X")
        )
        content = "\n".join(self.push_content) + "\n\n" + time_now
        notify.send(title, content)


def main():
    with open('config.toml', 'r', encoding='utf-8') as f:
        config = toml.load(f)

    for index, user in enumerate(config['users']):
        log.info('-------------------------------')
        log.info('检测到{}个账号，正在执行第{}个'.format(len(config['users']), index + 1))
        app = NUAA(user)
        status = app.run()
        log.info('打卡结果推送...')
        app.push(status)
