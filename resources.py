import re
import json
import time
import requests
import collections

yourcookie = ''

def prase(data):
    def tree():
        return collections.defaultdict(tree)

    out_dict = tree()
    time_name_list = []
    court_name_list = []
    for d in data:
        time_name_list.append(d['yaxis'])
        court_name_list.append(d['abscissa'])
    time_name_list = list(set(time_name_list))
    court_name_list = list(set(court_name_list))
    time_name_list.sort(key=lambda i: int(re.match(r'(\d+)', i).group()))
    court_name_list.sort(key=lambda i: int(re.match(r'(\d+)', i).group()))

    for time_name in time_name_list:
        for i, court_name in enumerate(court_name_list):
            for j, court in enumerate(data):
                if court['yaxis'] == time_name and i == 0:
                    out_dict['time_list'][time_name] = court['time_id']
            for k, court in enumerate(data):
                if court['yaxis'] == time_name and court['abscissa'] == court_name:
                    out_dict['court_list'][time_name][court_name] = court['sub_id']

    return out_dict


def main():
    resource_dict = {
        'resource_id': {
            '13': '明故宫校区 网球场',
            '14': '明故宫校区 羽毛球场',
            '15': '天目湖校区 羽毛球场',
            '16': '明故宫校区 乒乓球场',
            '17': '将军路校区 羽毛球场（体育馆）',
            '19': '将军路校区 羽毛球场（体育中心）',
            '20': '将军路校区 网球场',
        },
        'resource_list': {},
    }

    for resource_id in [13, 14, 15, 16, 17, 19, 20]:
        # for resource_id in [13]:
        print(f"处理{resource_dict['resource_id'][str(resource_id)]}...")
        url = f"https://ehall3.nuaa.edu.cn/site/reservation/resource-info-margin?resource_id={resource_id}&start_time=2022-04-22&end_time=2022-04-22"
        payload = {}
        headers = {
            'Host': 'ehall3.nuaa.edu.cn',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': yourcookie,
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ZhilinEai/2.8 ZhilinNuaaApp',
            'Referer': f'https://ehall3.nuaa.edu.cn/v2/reserve/m_reserveDetail?id={resource_id}',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=5
        )
        o_data = response.json()
        j_data = o_data['d']

        for key, value in j_data.items():
            resource_dict['resource_list'][str(resource_id)] = prase(value)
        time.sleep(2)
        print(f"{resource_dict['resource_id'][str(resource_id)]}处理结束")

    with open('resources.json', "w+", encoding='utf-8') as f:
        json.dump(resource_dict, f, ensure_ascii=False, indent=2, separators=(',', ':'))


if __name__ == '__main__':
    main()
