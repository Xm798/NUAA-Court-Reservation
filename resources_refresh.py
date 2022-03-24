import re
import time
import requests

yourcookie = ''


def output(f, data):
    t = []
    c = []
    for d in data:
        t.append(d['yaxis'])
        c.append(d['abscissa'])
    t = list(set(t))
    c = list(set(c))
    t.sort(key=lambda i: int(re.match(r'(\d+)', i).group()))
    c.sort(key=lambda i: int(re.match(r'(\d+)', i).group()))
    f.write('| ')
    for i in c:
        f.write(f'|{i}')
    f.write('|\n')
    for i in c:
        f.write('|:---:')
    f.write('|:---:|\n')
    for i in t:
        f.write(f'|{i}')
        for ij, j in enumerate(c):
            for ik, k in enumerate(data):
                if ij == 0 and k['yaxis'] == i:
                    f.write(f" (**{k['time_id']}**)|")
                    break
            for ik, k in enumerate(data):
                if k['yaxis'] == i and k['abscissa'] == j:
                    f.write(f"{k['sub_id']}|")
        f.write('\n\n')
    # f.write('\n</details>\n')


def request(*args, **kwargs):
    is_retry = True
    count = 0
    max_retries = 3
    sleep_seconds = 5
    while is_retry and count <= max_retries:
        try:
            s = requests.Session()
            requests.packages.urllib3.disable_warnings()
            response = s.request(*args, **kwargs, timeout=1, verify=False)
            is_retry = False
        except Exception as e:
            if count == max_retries:
                raise e
            print(f'Request failed: {e}')
            count += 1
            print(
                f'Trying to reconnect in {sleep_seconds} seconds ({count}/{max_retries})...'
            )
            time.sleep(sleep_seconds)
        else:
            return response


def main():
    court_name = {
        '13': '明故宫校区 网球',
        '14': '明故宫校区 羽毛球',
        '15': '天目湖校区 羽毛球',
        '16': '明故宫校区 乒乓球',
        '17': '将军路校区 羽毛球（体育馆）',
        '19': '将军路校区 羽毛球（体育中心）',
        '20': '将军路校区 网球',
    }

    f = open('resources.md', 'w+', encoding='utf-8')

    for i in [13, 14, 15, 16, 17, 19, 20]:
        url = f"https://ehall3.nuaa.edu.cn/site/reservation/resource-info-margin?resource_id={i}&start_time=2022-03-24&end_time=2022-03-24"
        payload = {}
        headers = {
            'Host': 'ehall3.nuaa.edu.cn',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': yourcookie,
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
            'Referer': 'https://ehall3.nuaa.edu.cn/v2/reserve/m_reserveDetail?id=19',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=5
        )
        o_data = response.json()
        j_data = o_data['d']
        # f.write(f"\n### {court_name[str(i)]} \n\n<details>\n<summary>展开详情</summary>\n\n")
        f.write(f"\n### {court_name[str(i)]} \n\n")
        for key, value in j_data.items():
            data = value
            print(data)
            output(f, data)
        time.sleep(1)


if __name__ == '__main__':
    main()
