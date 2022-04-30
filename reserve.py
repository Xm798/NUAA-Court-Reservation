# encoding=utf-8
import json
import re
import os
import time
import random
import uuid
import base64
from urllib.parse import urlencode
from __banner__ import banner
from notify import Notify
from config import config
from utils import log, time_now, request, start_time, stop_time


class App(object):
    def __init__(self, config):
        self.auth: dict = config['auth']
        self.cookie: dict = self.cookie_to_dict(self.auth.get('cookie'))
        self.refresh_token: str = self.auth.get('refresh_token')
        self.access_token: str = self.auth.get('access_token')
        self.username: str = self.auth.get('username')
        self.password: str = self.auth.get('password')
        self.name: str = ''
        self.imei: str = (
            self.auth.get('imei')
            if self.auth.get('imei')
            else str(uuid.uuid3(uuid.NAMESPACE_URL, str(self.auth))).upper()
        )

        self.push_content: list = []

    @staticmethod
    def cookie_to_dict(cookie) -> dict:
        try:
            if cookie and '=' in cookie:
                cookie = dict(
                    [line.strip().split('=', 1) for line in cookie.split(';')]
                )
        except Exception as e:
            log.error('Cookie 格式有误，请检查。')
            log.error(e)
            return {}
        else:
            return cookie

    @staticmethod
    def dict_to_str(cookie) -> str:
        if isinstance(cookie, dict):
            cookie_str = ""
            for i, (k, v) in enumerate(cookie.items()):
                append = f"{k}={v}" if i == len(cookie) - 1 else f"{k}={v}; "
                cookie_str += append
            return cookie_str

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
    def time_check() -> None:
        if time_now() < start_time:
            delta = float((start_time - time_now()).total_seconds())
            log.info(f'还未到开始时间，等待{delta}秒...')
            time.sleep(delta)

    def _log_push(self, level: str, content: str) -> None:
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
            self._log_push('error', '检查登录状态失败，未知原因，请查阅日志。')
            log.error(e)
            return False
        else:
            log.info(status.get('m'))
            if status.get('m') == '用户已登录':
                return True
            else:
                log.info(status)
                return False

    def login_app(self) -> bool:  # 登录i南航 APP 获取 refresh_token 和 access_token
        try:
            data = {
                "mobile_model": "iPhone14,2",
                "mobile_type": "ios",
                "app_version": "28.1",
                "mobile_version": "15.4.1",
                "imei": self.imei,  # 随机生成一个 iOS 设备识别码
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
                timeout=5,
                headers=headers,
                json=data,
            )
            eai_sess = re.search(
                r'(?<=(eai-sess=))[a-zA-Z0-9]+', login_stat.headers['Set-Cookie']
            ).group(0)
            uukey = re.search(
                r'(?<=(UUkey=))[a-zA-Z0-9]+', login_stat.headers['Set-Cookie']
            ).group(0)
            cookie_app = {'eai-sess': eai_sess, 'UUkey': uukey}

            form_data = {
                'imei': self.imei,
                'mobile_type': 'ios',
                'sid': self.imei,
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
                timeout=5,
                headers=headers,
                data=body,
                cookies=cookie_app,
            )
            login_result = r.json()

        except Exception as e:
            self._log_push('error', '登录i·南航失败，未知原因，请查阅日志。')
            log.error(e)
            return False

        else:
            if login_result['m'] == '操作成功':
                log.info(f"登录i·南航APP成功")
                self.refresh_token = login_result['d']['refresh_token']
                self.access_token = login_result['d']['access_token']
                return True
            elif login_result['m'] == '账户或密码错误':
                self._log_push('error', '账户或密码错误，登录i·南航APP失败。')
                return False
            elif login_result['m'] == '参数错误':
                self._log_push('error', '账户密码参数错误，登录i·南航APP失败，请检查配置。')
                return False
            else:
                self._log_push('error', '登录i·南航APP失败，未知原因，请查阅日志。')
                log.info(login_result.content.decode('utf-8', errors='ignore'))
                return False

    def get_cookie(self) -> bool:
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
            self._log_push('error', '登录预约系统失败，未知原因，请查阅日志。')
            log.error(e)
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
                self._log_push('error', '登录预约系统失败，可能是账号失效，请查阅日志。')
                log.error(e)
                return False
            else:
                self.cookie = {
                    'PHPSESSID': phpsessid,
                    'vjuid': vjuid,
                    'vjvd': vjvd,
                    'vt': vt,
                }
                if vjuid and vjvd and vt and phpsessid:
                    log.info('获取预约系统鉴权信息成功！')
                    return True
                else:
                    self._log_push('error', '获取预约系统鉴权信息失败，请查阅日志。')
                    log.error(response.headers)
                    return False

    def get_name(self) -> bool:
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
                cookies=self.cookie,
                headers=headers,
            )
        except Exception as e:
            log.info('姓名获取失败。')
            log.error(e)
            return False
        else:
            response.encoding = 'utf-8'
            r = response.json()
            try:
                self.name = r['d'].get('name')
                self.username = r['d'].get('number')
                log.info(f'账号：{self.name} {self.username}')
                return True
            except Exception as e:
                log.info('姓名获取失败。')
                log.error(e)
                return False

    def captcha(self) -> str:
        try:
            timestamp = int(time.time() * 1000)
            url = 'https://ehall3.nuaa.edu.cn/site/login/code?v=' + str(timestamp)
            headers = {
                'Accept': 'image/webp,image/png,image/svg+xml,image/*;q=0.8,video/*;q=0.8,*/*;q=0.5',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
                'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
                'Referer': 'https://ehall3.nuaa.edu.cn/v2/reserve/m_reserveDetail?id='
                + str(config.court_id),
                'Accept-Encoding': 'gzip, deflate, br',
            }
            response = request(
                'get',
                url,
                cookies=self.cookie,
                headers=headers,
            )
            captcha_pic = base64.b64encode(response.content)
        except Exception as e:
            log.error('验证码获取错误。')
            log.error(e)
            return ''
        else:
            try:
                basic_url = os.environ.get(
                    'COURT_RESERVATION_OCR_API', 'https://cocr.xm.mk/'
                )
                url = (
                    basic_url + "ocr/b64/text"
                    if basic_url.endswith('/')
                    else basic_url + "/ocr/b64/text"
                )
                r = request('POST', url, data=captcha_pic)
                result = r.text
            except Exception as e:
                log.error('验证码识别接口出错。')
                log.error(e)
                return ''
            else:
                log.info(f'验证码识别成功，{result}')
                return result

    def reserve(self, index, court_data):
        try:
            captcha = self.captcha()
            body = {
                'resource_id': config.court_id,
                'code': captcha,
                'remarks': '',
                'deduct_num': '',
                'data': f'[{json.dumps(court_data)}]',
            }
            # log.debug(f'请求体：{body}')
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
                cookies=self.cookie,
                headers=headers,
            )
            response.encoding = 'utf-8'
        except Exception as e:
            self._log_push('error', '提交预约失败！详情见日志。')
            log.error(e)
            return 0
        else:
            r = response.json()
            fail_info = f"{config.courts_list_readable[index]['period']} 的 {config.courts_list_readable[index]['sub_resource_id']} 场地预约失败，原因为{r['m']}。"
            if r['m'] == '操作成功':
                self._log_push(
                    'info',
                    f"{config.courts_list_readable[index]['period']} 的 {config.courts_list_readable[index]['sub_resource_id']} 场地预约成功！",
                )
                return 1
            elif r['m'] == '验证码错误':
                log.warning('验证码错误，正在重试...')
                return 0
            elif r['m'] == "不在服务时间":
                if time_now() > stop_time:
                    self._log_push('info', fail_info)
                    return -1
                else:
                    log.info(f"不在服务时间，正在重试...")
                    return 0
            else:
                self._log_push('info', fail_info)
                return -1

    def launch_reserve(self, index, court):
        ret_code = self.reserve(index, court)
        i = 0
        while ret_code == 0 and i < 5:
            time.sleep(0.1)
            ret_code = self.reserve(index, court)
            i += 1
        return ret_code

    def log_with_password(self):
        if self.password and self.password:
            if self.login_app():
                log.info('统一身份认证：登录成功！')
                return True
            else:
                log.info('统一身份认证：登录失败。')
                return False
        return False

    def login(self):
        log.info('正在登录体育场地预约系统...')

        if self.cookie:
            log.info('登录方式：办事大厅 Cookie')
            if self.cookie.get('PHPSESSID'):
                log.info('获取用户基本信息...')
                if self.get_name():
                    return True
            else:
                log.info('Cookie不完整，即将重新获取...')

        if self.access_token and self.refresh_token:  # 使用 Token 登录
            log.info('登录方式：i·南航 Token')
            log.info('正在检查 Token...')
            if not self.check_token():
                log.info('Token 失效，尝试重新获取...')
                if not self.log_with_password():
                    return False
            else:
                log.info('Token 有效...')
        else:
            if self.username and self.password:
                log.info('登录方式：统一身份认证账密')
                if not self.log_with_password():
                    return False

        log.info('获取预约系统鉴权信息...')
        if self.get_cookie():
            log.info('获取用户基本信息...')
            self.get_name()
            return True
        else:
            return False

    def run(self):
        if self.login():
            log.info('登录预约系统成功！')
        else:
            log.info('登录预约系统失败。')
            return False
        self.time_check()
        log.info('提交预约申请...')
        for index, court in enumerate(config.courts_list):
            result = self.launch_reserve(index, court)
            if result == 1:  # 预约成功
                return True
            elif result == -1:  # 预约失败，换个场地
                time.sleep(0.2)  # 稍微歇会
        return False

    def push(self, status):
        notify = Notify(config.notify)
        title = '体育场地预约小助手：预约成功！' if status else '体育场地预约小助手：预约失败！'
        content = (
            f"账号：{self.name} {self.username}\n"
            + f"场馆：{config.resources['resource_id'][config.court_id]}\n\n"
            + "预约详情：\n"
            + "\n".join(self.push_content)
            + "\n\n"
            + time_now().strftime("%Y-%m-%d %X")
        )
        notify.send(title, content)

    # def config_auth_update(self) -> dict:  # 返回 config.user.auth 字典
    #     auth_update = {
    #         'cookie': self.dict_to_str(self.cookie),
    #         'refresh_token': self.refresh_token,
    #         'access_token': self.access_token,
    #         'imei': self.imei,
    #     }
    #     self.auth.update(auth_update)
    #     return self.auth


def main():
    log.info(banner)
    config.init()
    app = App(config)
    status = app.run()
    log.info('结果推送...')
    app.push(status)
    # config.auth.update(app.config_auth_update())
    # config.dump_config()
