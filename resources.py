import re
import json
import time
import requests
import collections


def to_markdown(f, data):
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
        f.write('\n')


def parse(data):
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

    f_md = open('resources.md', 'w+', encoding='utf-8')

    for resource_id in [13, 14, 15, 16, 17, 19, 20]:
        # for resource_id in [13]:
        print(f"处理{resource_dict['resource_id'][str(resource_id)]}...")
        url = f"https://ehall3.nuaa.edu.cn/site/reservation/resource-info-margin?resource_id={resource_id}&start_time=2022-04-30&end_time=2022-04-30"
        payload = {}
        headers = {
            'Host': 'ehall3.nuaa.edu.cn',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': '',
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

        f_md.write(f"\n### {resource_dict['resource_id'][str(resource_id)]} \n\n")
        for key, value in j_data.items():
            data = value
            print(data)
            to_markdown(f_md, data)

        for key, value in j_data.items():
            resource_dict['resource_list'][str(resource_id)] = parse(value)
        print(f"{resource_dict['resource_id'][str(resource_id)]}处理结束")

        time.sleep(3)

    with open('resources.json', "w+", encoding='utf-8') as f_json:
        json.dump(resource_dict, f_json, ensure_ascii=False, indent=2, separators=(',', ':'))
        f_json.close()
    f_md.close()


if __name__ == '__main__':
    main()
