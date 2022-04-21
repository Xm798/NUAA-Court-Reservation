#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
import logging
import base64
import hashlib
import hmac
import json
import os
import re
import threading
import time
import urllib.parse

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

log = logging


class Notify(object):
    def __init__(self, custom_config: dict = None):
        self.push_config = {
            'BARK_PUSH': '',  # bark IP 或设备码，例：https://api.day.app/DxHcxxxxxRxxxxxxcm/
            'BARK_ARCHIVE': '',  # bark 推送是否存档
            'BARK_GROUP': '',  # bark 推送分组
            'BARK_SOUND': '',  # bark 推送声音
            'BARK_ICON': '',  # bark 推送图标
            'DD_BOT_SECRET': '',  # 钉钉机器人的 DD_BOT_SECRET
            'DD_BOT_TOKEN': '',  # 钉钉机器人的 DD_BOT_TOKEN
            'FSKEY': '',  # 飞书机器人的 FSKEY
            'CQHTTP_URL': '',  # go-cqhttp
            # 推送到个人QQ：http://127.0.0.1/send_private_msg
            # 群：http://127.0.0.1/send_group_msg
            'CQHTTP_QQ': '',  # go-cqhttp 的推送群或用户
            # CQHTTP_URL 设置 /send_private_msg 时填入 user_id=个人QQ
            #               /send_group_msg   时填入 group_id=QQ群
            'CQHTTP_TOKEN': '',  # go-cqhttp 的 access_token
            'GOTIFY_URL': '',  # gotify地址,如https://push.example.de:8080
            'GOTIFY_TOKEN': '',  # gotify的消息应用token
            'GOTIFY_PRIORITY': 0,  # 推送消息优先级,默认为0
            'IGOT_PUSH_KEY': '',  # iGot 聚合推送的 IGOT_PUSH_KEY
            'SCT_KEY': '',  # server 酱的 PUSH_KEY
            'PUSH_PLUS_TOKEN': '',  # push+ 微信推送的用户令牌
            'PUSH_PLUS_USER': '',  # push+ 微信推送的群组编码
            'QMSG_KEY': '',  # qmsg 酱的 QMSG_KEY
            'QMSG_TYPE': '',  # qmsg 酱的 QMSG_TYPE
            'QYWX_AM': '',  # 企业微信应用
            'QYWX_KEY': '',  # 企业微信机器人
            'TG_BOT_TOKEN': '',  # tg 机器人的 TG_BOT_TOKEN，例：1407203283:AAG9rt-6RDaaX0HBLZQq0laNOh898iFYaRQ
            'TG_USER_ID': '',  # tg 机器人的 TG_USER_ID，例：1434078534
            'TG_API_HOST': '',  # tg 代理 api
            'TG_PROXY_AUTH': '',  # tg 代理认证参数
            'TG_PROXY_HOST': '',  # tg 机器人的 TG_PROXY_HOST
            'TG_PROXY_PORT': '',  # tg 机器人的 TG_PROXY_PORT
        }
        self.notify_function = []

        # 优先从环境变量获取配置
        for k in self.push_config:
            if os.getenv(k):
                v = os.getenv(k)
                self.push_config[k] = v

        # 读入配置文件设置，覆盖环境变量配置
        if custom_config:
            self.push_config.update(custom_config)

        # 创建推送任务队列
        if self.push_config.get("BARK_PUSH"):
            self.notify_function.append(self.bark)
        if self.push_config.get("DD_BOT_TOKEN") and self.push_config.get("DD_BOT_SECRET"):
            self.notify_function.append(self.dingding_bot)
        if self.push_config.get("FSKEY"):
            self.notify_function.append(self.feishu_bot)
        if self.push_config.get("CQHTTP_URL") and self.push_config.get("CQHTTP_QQ"):
            self.notify_function.append(self.go_cqhttp)
        if self.push_config.get("GOTIFY_URL") and self.push_config.get("GOTIFY_TOKEN"):
            self.notify_function.append(self.gotify)
        if self.push_config.get("IGOT_PUSH_KEY"):
            self.notify_function.append(self.igot)
        if self.push_config.get("SCT_KEY"):
            self.notify_function.append(self.server_chan)
        if self.push_config.get("PUSH_PLUS_TOKEN"):
            self.notify_function.append(self.pushplus_bot)
        if self.push_config.get("QMSG_KEY") and self.push_config.get("QMSG_TYPE"):
            self.notify_function.append(self.qmsg_bot)
        if self.push_config.get("QYWX_AM"):
            self.notify_function.append(self.wecom_app)
        if self.push_config.get("QYWX_KEY"):
            self.notify_function.append(self.wecom_bot)
        if self.push_config.get("TG_BOT_TOKEN") and self.push_config.get("TG_USER_ID"):
            self.notify_function.append(self.telegram_bot)

    def bark(self, title: str, content: str) -> None:
        """
        使用 bark 推送消息。
        """
        if not self.push_config.get("BARK_PUSH"):
            log.warning("bark 服务的 BARK_PUSH 未设置!!\n取消推送")
            return
        log.info("bark 服务启动")

        if self.push_config.get("BARK_PUSH").startswith("http"):
            url = f'{self.push_config.get("BARK_PUSH")}/{urllib.parse.quote_plus(title)}/{urllib.parse.quote_plus(content)}'
        else:
            url = f'https://api.day.app/{self.push_config.get("BARK_PUSH")}/{urllib.parse.quote_plus(title)}/{urllib.parse.quote_plus(content)}'

        bark_params = {
            "BARK_ARCHIVE": "isArchive",
            "BARK_GROUP": "group",
            "BARK_SOUND": "sound",
            "BARK_ICON": "icon",
        }
        params = ""
        for pair in filter(
                lambda pairs: pairs[0].startswith("BARK_")
                              and pairs[0] != "BARK_PUSH"
                              and pairs[1]
                              and bark_params.get(pairs[0]),
                self.push_config.items(),
        ):
            params += f"{bark_params.get(pair[0])}={pair[1]}&"
        if params:
            url = url + "?" + params.rstrip("&")
        response = requests.get(url).json()

        if response["code"] == 200:
            log.info("bark 推送成功！")
        else:
            log.error("bark 推送失败！")

    def dingding_bot(self, title: str, content: str) -> None:
        """
        使用 钉钉机器人 推送消息。
        """
        if not self.push_config.get("DD_BOT_SECRET") or not self.push_config.get(
                "DD_BOT_TOKEN"
        ):
            log.warning("钉钉机器人 服务的 DD_BOT_SECRET 或者 DD_BOT_TOKEN 未设置!!\n取消推送")
            return
        log.info("钉钉机器人 服务启动")

        timestamp = str(round(time.time() * 1000))
        secret_enc = self.push_config.get("DD_BOT_SECRET").encode("utf-8")
        string_to_sign = "{}\n{}".format(
            timestamp, self.push_config.get("DD_BOT_SECRET")
        )
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(
            secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f'https://oapi.dingtalk.com/robot/send?access_token={self.push_config.get("DD_BOT_TOKEN")}&timestamp={timestamp}&sign={sign}'
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if not response["errcode"]:
            log.info("钉钉机器人 推送成功！")
        else:
            log.error("钉钉机器人 推送失败！")

    def feishu_bot(self, title: str, content: str) -> None:
        """
        使用 飞书机器人 推送消息。
        """
        if not self.push_config.get("FSKEY"):
            log.warning("飞书 服务的 FSKEY 未设置!!\n取消推送")
            return
        log.info("飞书 服务启动")

        url = f'https://open.feishu.cn/open-apis/bot/v2/hook/{self.push_config.get("FSKEY")}'
        data = {"msg_type": "text", "content": {"text": f"{title}\n\n{content}"}}
        response = requests.post(url, data=json.dumps(data)).json()

        if response.get("StatusCode") == 0:
            log.info("飞书 推送成功！")
        else:
            log.error("飞书 推送失败！错误信息如下：\n", response)

    def go_cqhttp(self, title: str, content: str) -> None:
        """
        使用 go_cqhttp 推送消息。
        """
        if not self.push_config.get("CQHTTP_URL") or not self.push_config.get(
                "CQHTTP_QQ"
        ):
            log.warning("go-cqhttp 服务的 CQHTTP_URL 或 CQHTTP_QQ 未设置!!\n取消推送")
            return
        log.info("go-cqhttp 服务启动")

        url = f'{self.push_config.get("CQHTTP_URL")}?{self.push_config.get("CQHTTP_QQ")}&message={title}\n\n{content}'
        headers = {'Authorization': self.push_config.get("CQHTTP_TOKEN")}
        response = requests.get(url, headers=headers).json()

        if response["status"] == "ok":
            log.info("go-cqhttp 推送成功！")
        else:
            log.error("go-cqhttp 推送失败！")

    def gotify(self, title: str, content: str) -> None:
        """
        使用 gotify 推送消息。
        """
        if not self.push_config.get("GOTIFY_URL") or not self.push_config.get(
                "GOTIFY_TOKEN"
        ):
            log.warning("gotify 服务的 GOTIFY_URL 或 GOTIFY_TOKEN 未设置!!\n取消推送")
            return
        log.info("gotify 服务启动")

        url = f'{self.push_config.get("GOTIFY_URL")}/message?token={self.push_config.get("GOTIFY_TOKEN")}'
        data = {
            "title": title,
            "message": content,
            "priority": self.push_config.get("GOTIFY_PRIORITY"),
        }
        response = requests.post(url, data=data).json()

        if response.get("id"):
            log.info("gotify 推送成功！")
        else:
            log.error("gotify 推送失败！")

    def igot(self, title: str, content: str) -> None:
        """
        使用 iGot 推送消息。
        """
        if not self.push_config.get("IGOT_PUSH_KEY"):
            log.warning("iGot 服务的 IGOT_PUSH_KEY 未设置!!\n取消推送")
            return
        log.info("iGot 服务启动")

        url = f'https://push.hellyw.com/{self.push_config.get("IGOT_PUSH_KEY")}'
        data = {"title": title, "content": content}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=data, headers=headers).json()

        if response["ret"] == 0:
            log.info("iGot 推送成功！")
        else:
            log.error(f'iGot 推送失败！{response["errMsg"]}')

    def server_chan(self, title: str, content: str) -> None:
        """
        通过 serverJ 推送消息。
        """
        if not self.push_config.get("SCT_KEY"):
            log.warning("server 酱服务的 SCT_KEY 未设置!!\n取消推送")
            return
        log.info("server 酱服务启动")

        data = {"text": title, "desp": content.replace("\n", "\n\n")}
        if self.push_config.get("SCT_KEY").index("SCT") != -1:
            url = f'https://sctapi.ftqq.com/{self.push_config.get("SCT_KEY")}.send'
        else:
            url = f'https://sc.ftqq.com/${self.push_config.get("SCT_KEY")}.send'
        response = requests.post(url, data=data).json()

        if response.get("errno") == 0 or response.get("code") == 0:
            log.info("server 酱推送成功！")
        else:
            log.error(f'server 酱推送失败！错误码：{response["message"]}')

    def pushplus_bot(self, title: str, content: str) -> None:
        """
        通过 push+ 推送消息。
        """
        if not self.push_config.get("PUSH_PLUS_TOKEN"):
            log.warning("PUSHPLUS 服务的 PUSH_PLUS_TOKEN 未设置!!\n取消推送")
            return
        log.info("PUSHPLUS 服务启动")

        url = "https://www.pushplus.plus/send"
        data = {
            "token": self.push_config.get("PUSH_PLUS_TOKEN"),
            "title": title,
            "content": content,
            'template': 'txt',
            "topic": self.push_config.get("PUSH_PLUS_USER"),
        }
        body = json.dumps(data).encode(encoding="utf-8")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url=url, data=body, headers=headers).json()

        if response["code"] == 200:
            log.info("PUSHPLUS 推送成功！")

        else:
            log.error("PUSHPLUS 推送失败！")

    def qmsg_bot(self, title: str, content: str) -> None:
        """
        使用 qmsg 推送消息。
        """
        if not self.push_config.get("QMSG_KEY") or not self.push_config.get(
                "QMSG_TYPE"
        ):
            log.warning("qmsg 的 QMSG_KEY 或者 QMSG_TYPE 未设置!!\n取消推送")
            return
        log.info("qmsg 服务启动")

        url = f'https://qmsg.zendee.cn/{self.push_config.get("QMSG_TYPE")}/{self.push_config.get("QMSG_KEY")}'
        payload = {"msg": f'{title}\n\n{content.replace("----", "-")}'.encode("utf-8")}
        response = requests.post(url=url, params=payload).json()

        if response["code"] == 0:
            log.info("qmsg 推送成功！")
        else:
            log.error(f'qmsg 推送失败！{response["reason"]}')

    def wecom_app(self, title: str, content: str) -> None:
        """
        通过 企业微信 APP 推送消息。
        """
        if not self.push_config.get("QYWX_AM"):
            log.warning("QYWX_AM 未设置!!\n取消推送")
            return
        qywx_am_ay = re.split(",", self.push_config.get("QYWX_AM"))
        if 4 < len(qywx_am_ay) > 5:
            log.error("QYWX_AM 设置错误!!\n取消推送")
            return
        log.info("企业微信 APP 服务启动")

        corpid = qywx_am_ay[0]
        corpsecret = qywx_am_ay[1]
        touser = qywx_am_ay[2]
        agentid = qywx_am_ay[3]
        try:
            media_id = qywx_am_ay[4]
        except IndexError:
            media_id = ""
        wx = self.WeCom(corpid, corpsecret, agentid)
        # 如果没有配置 media_id 默认就以 text 方式发送
        if not media_id:
            message = title + "\n\n" + content
            response = wx.send_text(message, touser)
        else:
            response = wx.send_mpnews(title, content, media_id, touser)

        if response == "ok":
            log.info("企业微信推送成功！")
        else:
            log.error("企业微信推送失败！错误信息如下：\n", response)

    class WeCom:
        def __init__(self, corpid, corpsecret, agentid):
            self.CORPID = corpid
            self.CORPSECRET = corpsecret
            self.AGENTID = agentid

        def get_access_token(self):
            url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            values = {
                "corpid": self.CORPID,
                "corpsecret": self.CORPSECRET,
            }
            req = requests.post(url, params=values)
            data = json.loads(req.text)
            return data["access_token"]

        def send_text(self, message, touser="@all"):
            send_url = (
                    "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="
                    + self.get_access_token()
            )
            send_values = {
                "touser": touser,
                "msgtype": "text",
                "agentid": self.AGENTID,
                "text": {"content": message},
                "safe": "0",
            }
            send_msgs = bytes(json.dumps(send_values), "utf-8")
            response = requests.post(send_url, send_msgs)
            response = response.json()
            return response["errmsg"]

        def send_mpnews(self, title, message, media_id, touser="@all"):
            send_url = (
                    "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="
                    + self.get_access_token()
            )
            send_values = {
                "touser": touser,
                "msgtype": "mpnews",
                "agentid": self.AGENTID,
                "mpnews": {
                    "articles": [
                        {
                            "title": title,
                            "thumb_media_id": media_id,
                            "author": "Author",
                            "content_source_url": "",
                            "content": message.replace("\n", "<br/>"),
                            "digest": message,
                        }
                    ]
                },
            }
            send_msges = bytes(json.dumps(send_values), "utf-8")
            respone = requests.post(send_url, send_msges)
            respone = respone.json()
            return respone["errmsg"]

    def wecom_bot(self, title: str, content: str) -> None:
        """
        通过 企业微信机器人 推送消息。
        """
        if not self.push_config.get("QYWX_KEY"):
            log.warning("企业微信机器人 服务的 QYWX_KEY 未设置!!\n取消推送")
            return
        log.info("企业微信机器人服务启动")

        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.push_config.get('QYWX_KEY')}"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if response["errcode"] == 0:
            log.info("企业微信机器人推送成功！")
        else:
            log.error("企业微信机器人推送失败！")

    def telegram_bot(self, title: str, content: str) -> None:
        """
        使用 telegram 机器人 推送消息。
        """
        if not self.push_config.get("TG_BOT_TOKEN") or not self.push_config.get(
                "TG_USER_ID"
        ):
            log.warning("Telegram 服务的 bot_token 或者 user_id 未设置!!\n取消推送")
            return
        log.info("Telegram 服务启动")

        if self.push_config.get("TG_API_HOST"):
            url = f"https://{self.push_config.get('TG_API_HOST')}/bot{self.push_config.get('TG_BOT_TOKEN')}/sendMessage"
        else:
            url = f"https://api.telegram.org/bot{self.push_config.get('TG_BOT_TOKEN')}/sendMessage"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "chat_id": str(self.push_config.get("TG_USER_ID")),
            "text": f"<b>{title}</b>\n\n{content}",
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
        proxies = None
        if self.push_config.get("TG_PROXY_HOST") and self.push_config.get(
                "TG_PROXY_PORT"
        ):
            if self.push_config.get(
                    "TG_PROXY_AUTH"
            ) is not None and "@" not in self.push_config.get("TG_PROXY_HOST"):
                self.push_config["TG_PROXY_HOST"] = (
                        self.push_config.get("TG_PROXY_AUTH")
                        + "@"
                        + self.push_config.get("TG_PROXY_HOST")
                )
            proxy_str = "http://{}:{}".format(
                self.push_config.get("TG_PROXY_HOST"),
                self.push_config.get("TG_PROXY_PORT"),
            )
            proxies = {"http": proxy_str, "https": proxy_str}
        response = requests.post(
            url=url, headers=headers, params=payload, proxies=proxies
        ).json()

        if response["ok"]:
            log.info("Telegram 推送成功！")
        else:
            log.error("Telegram 推送失败！")

    def send(self, title: str, content: str) -> None:
        if not content:
            log.info(f"{title} 推送内容为空！")
            return

        ts = [
            threading.Thread(target=mode, args=(title, content), name=mode.__name__)
            for mode in self.notify_function
        ]
        [t.start() for t in ts]
        [t.join() for t in ts]
