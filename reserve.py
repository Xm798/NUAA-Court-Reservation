# encoding=utf-8
import json
import logging
import re
import time
import requests
import toml
import random
import string
import uuid
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
    max_retries = 50
    sleep_seconds = 3
    while is_retry and count <= max_retries:
        try:
            s = requests.Session()
            response = s.request(*args, **kwargs, timeout=2)
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
        self.refresh_token: str = user['auth'].get('refresh_token')
        self.access_token: str = user['auth'].get('access_token')
        self.username: str = user['auth'].get('username')
        self.password: str = user['auth'].get('password')
        self.cookie_app: dict = {}
        self.cookie_ehall: dict = {}
        self.name: str = ''
        self.court_id: int = user['court_id']  # 场地类型
        self.court_list: list = user['clout_list']  # 场地列表
        self.notify_conf: dict = user['notify']
        self.push_content: list = []

    @staticmethod
    def cookie_to_dict(cookie) -> dict:
        try:
            if cookie and '=' in cookie:
                cookie = dict(
                    [line.strip().split('=', 1) for line in cookie.split(';')]
                )
        except Exception as e:
            log.error('Cookie 格式有误，请检查')
            log.debug(e)
            return None
        else:
            return cookie

    @staticmethod
    def encode_multipart_formdata(fields):
        boundary = "Boundary+" + ''.join(random.sample('0123456789ABCDEF', 16))
        crlf = '\r\n'
        li = []
        for (key, value) in fields.items():
            li.append('--' + boundary)
            li.append('Content-Disposition: form-data; name="%s"' % key)
            li.append('')
            li.append(value)
        li.append('--' + boundary + '--')
        li.append('')
        body = crlf.join(li)
        content_type = 'multipart/form-data; boundary=%s' % boundary
        return content_type, body

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

    def _log_push(self, level: str, content: str):
        if level == 'info':
            log.info(content)
        elif level == 'error':
            log.error(content)
        elif level == 'warning':
            log.warning(content)
        else:
            log.debug(content)
        self.push_content.append(content)

    def check_token(self) -> bool:
        try:
            headers = {
                'Host': 'm.nuaa.edu.cn',
                'Connection': 'keep-alive',
                'Accept': '*/*',
                'User-Agent': 'MobileCampus/2.8 (iPhone; iOS 15.4.1; Scale/3.00)',
                'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9, zh-Hant-CN;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            params = {'token': self.access_token, 'xgh': self.username}
            r = request(
                'get',
                'https://m.nuaa.edu.cn/nuaaappv2/wap/default/check-token',
                headers=headers,
                params=params,
            )
            status = r.json()
        except Exception as e:
            self._log_push('error', '检查登录状态失败，未知原因，请查阅 debug 日志')
            log.debug(e)
            return False
        else:
            log.info(status.get('m'))
            if status.get('m') == '用户已登录':
                return True
            else:
                return False

    def login_app(self) -> bool:
        try:
            data = {
                "mobile_model": "iPhone14,2",
                "mobile_type": "ios",
                "app_version": "28.1",
                "mobile_version": "15.4.1",
                "imei": str(uuid.uuid1()).upper(),  # 随机生成一个 iOS 设备识别码
            }
            headers = {
                'Host': 'm.nuaa.edu.cn',
                'Content-Type': 'application/json',
                'Connection': 'keep-alive',
                'Accept': '*/*',
                'User-Agent': 'MobileCampus/2.8 (iPhone; iOS 15.4.1; Scale/3.00)',
                'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9, zh-Hant-CN;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            login_stat = request(
                'post',
                'https://m.nuaa.edu.cn/nuaaappv2/wap/install-stat/insert',
                headers=headers,
                json=data,
            )
            eai_sess = re.search(
                r'(?<=(eai-sess=))[a-zA-Z0-9]+', login_stat.headers['Set-Cookie']
            ).group(0)
            uukey = re.search(
                r'(?<=(UUkey=))[a-zA-Z0-9]+', login_stat.headers['Set-Cookie']
            ).group(0)
            self.cookie_app = {'eai-sess': eai_sess, 'UUkey': uukey}

            form_data = {
                'imei': data['imei'],
                'mobile_type': 'ios',
                'sid': data['imei'],
                'username': self.username,
                'password': self.password,
            }
            content_type, body = self.encode_multipart_formdata(form_data)
            headers = {
                'Host': 'm.nuaa.edu.cn',
                'Content-Type': content_type,
                'Connection': 'keep-alive',
                'Accept': '*/*',
                'User-Agent': 'MobileCampus/2.8 (iPhone; iOS 15.4.1; Scale/3.00)',
                'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9, zh-Hant-CN;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            r = request(
                'post',
                'https://m.nuaa.edu.cn/a_nuaa/api/login-v2/index',
                headers=headers,
                data=body,
                cookies=self.cookie_app,
            )
            login_result = r.json()

        except Exception as e:
            self._log_push('error', '登录i·南航失败，未知原因，请查阅 debug 日志')
            log.debug(e)
            return False

        else:
            if login_result['m'] == '操作成功':
                log.info(f"{login_result['d']['name']}，登录成功")
                self.refresh_token = login_result['d']['refresh_token']
                self.access_token = login_result['d']['access_token']
                return True
            elif login_result['m'] == '账户或密码错误':
                self._log_push('error', '账户或密码错误，登录i·南航失败')
                return False
            elif login_result['m'] == '参数错误':
                self._log_push('error', '账户密码参数错误，登录i·南航失败，请检查配置')
                return False
            else:
                self._log_push('error', '登录i·南航失败，未知原因，请查阅 debug 日志')
                log.debug(login.content.decode('utf-8', errors='ignore'))
                return False

    def get_ehall_cookie(self) -> bool:
        try:
            headers = {
                'Host': 'ehall3.nuaa.edu.cn',
                'Accept-Encoding': 'gzip, deflate, br',
                'deviceType': 'ios',
                'refresh_token': self.refresh_token,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
                'token': self.access_token,
                'access_token': self.access_token,
                'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            }
            response = request(
                "GET",
                'https://ehall3.nuaa.edu.cn/api/login/nuaa-app-login?redirect=https://m.nuaa.edu.cn/site/applicationSquare/index?sid=7',
                headers=headers,
                allow_redirects=False,
            )
        except Exception as e:
            self._log_push('error', '登录预约系统失败，未知原因，请查阅 debug 日志')
            log.debug(e)
            return False
        else:
            try:
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
            except Exception as e:
                self._log_push('error', '登录预约系统失败，可能是账号失效，请查阅 debug 日志')
                log.debug(e)
                return False
            else:
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
                    self._log_push('error', '获取预约系统鉴权信息失败，请查阅 debug 日志')
                    log.debug(response.headers)
                    return False

    def get_name(self):
        try:
            headers = {
                'Host': 'ehall3.nuaa.edu.cn',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
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
        except Exception as e:
            log.info('姓名获取失败')
            log.debug(e)
        else:
            response.encoding = 'utf-8'
            r = response.json()
            try:
                name = r['d'].get('name')
                number = r['d'].get('number')
                self.push_content.append(f'账号：{name} {number}')
            except Exception as e:
                log.info('姓名获取失败')
                log.debug(e)
                return

    def reserve(self, court_data):
        try:
            # code = (''.join(random.sample(string.ascii_letters + string.digits, 5))) + str(random.randint(0,9))
            body = {
                'resource_id': self.court_id,
                'code': '',
                'remarks': "",
                'deduct_num': "",
                'data': f'[{json.dumps(court_data)}]',
            }
            print(body)
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
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
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
            self._log_push('error', '提交预约失败！详情见 debug 日志。')
            log.debug(e)
        else:
            r = response.json()
            fail_info = f"id为{court_data['sub_resource_id']}，时间为{court_data['period']}的场地预约失败，原因为{r['m']}"
            if r['m'] == '操作成功':
                self._log_push(
                    'info',
                    f"id为{court_data['sub_resource_id']}，时间为{court_data['period']}的场地预约成功",
                )
                return 1
            elif r['m'] == "不在服务时间":
                self._log_push('info', fail_info)
                now = (
                    datetime.utcnow()
                    .replace(tzinfo=timezone.utc)
                    .astimezone(timezone(timedelta(hours=8)))
                )
                stop_time = datetime.combine(
                    now.date(), datetime.strptime("21:00:00", "%H:%M:%S").time()
                ).replace(tzinfo=timezone(timedelta(hours=8)))
                if now > stop_time:
                    return -1
                else:
                    return 0
            else:  # r['m'] == '预约日期已约满' or r['m'] == '预约日期已被禁用':
                self._log_push('info', fail_info)
                return -1

    def launch_reserve(self, court):
        i = self.reserve(court)
        while i == 0:
            time.sleep(1)
            i = self.reserve(court)
        return i

    def run(self):
        if self.refresh_token and self.access_token:
            log.info('正在检查 Token...')
            if not self.check_token():
                log.info('Token 失效，尝试重新获取...')
                if not self.login_app():
                    return False
            else:
                log.info('Token 检查成功...')
        else:
            log.info('没有 Token，尝试重新获取...')
            if not self.login_app():
                return False

        log.info('获取预约系统鉴权信息...')
        if not self.get_ehall_cookie():
            return False
        log.info('获取用户基本信息...')
        self.time_check()
        # log.info('提交预约申请...')
        # for court in self.court_list:
        #     result = self.launch_reserve(court)
        #     if result == 1:  # 预约成功
        #         return True
        #     elif result == -1:  # 预约失败，换个场地
        #         time.sleep(2)  # 稍微歇会
        # return False

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
