import asyncio
import re
import urllib.parse

import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
import aiohttp

global browser, wait, tasks


# 初始化
def init():
    option = Options()
    option.add_argument('--disable-blink-features=AutomationControlled')
    option.add_argument("--headless")
    option.add_argument("--disbale-gpu")
    # 定义为全局变量，方便其他模块使用
    global browser, wait
    # 实例化一个chrome浏览器
    browser = webdriver.Chrome(options=option)
    # 设置等待超时
    wait = WebDriverWait(browser, 20)


# 拿到的cookie只是一部分
def get_part_cookie():
    browser.get("https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc")
    c = browser.get_cookies()
    cookies = ''
    # 获取cookie中的name和value,转化成requests可以使用的形式
    for cookie in c:
        cookies += "{}={};".format(cookie['name'], cookie['value'])

    return cookies


def get_another_cookie(stationName, date, from_station, to_station):
    from_station_code = stationName[from_station]
    to_station_code = stationName[to_station]
    from_station_str = from_station + "," + from_station_code
    to_station_str = to_station + "," + to_station_code
    from_station_escape = escape(from_station_str)
    to_station_escape = escape(to_station_str)
    another_cookie = ("_jc_save_fromStation={};"
                      "_jc_save_toStation={};"
                      "_jc_save_fromDate={};"
                      " _jc_save_toDate={};"
                      "_jc_save_wfdc_flag=dc").format(from_station_escape, to_station_escape, date, date)
    return another_cookie


def get_all_station_name_and_code():
    station_name_source = requests.get(
        ' https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9235')
    pattern = r'([\u4e00-\u9fa5]+)\|([A-Z]+)'  # 正则匹配规则
    result = re.findall(pattern, station_name_source.text)
    stationName = dict(result)  # 所有车站信息，转换为字典
    stationCode = dict(zip(stationName.values(), stationName.keys()))
    return stationName, stationCode


# 构建用于查询列车车次信息的url
def get_query_url(stationName, date, from_station, to_station):
    # key为车站名称， value为车站代号

    from_station = stationName[from_station]
    to_station = stationName[to_station]
    # 构造直接获取车次信息的url
    query_url = ("https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={}"
                 "&leftTicketDTO.from_station={}"
                 "&leftTicketDTO.to_station={}"
                 "&purpose_codes=ADULT"
                 ).format(date, from_station, to_station)
    return query_url


def escape(data):
    fill = re.findall('[\u4e00-\u9fa5]', data)
    if len(fill) > 0:
        for ch in fill:
            data = data.replace(ch, '5Cu{0}'.format(hex(ord(ch))[2:].upper()))
    return urllib.parse.quote(data.encode('unicode-escape'), safe='*@-_+./').replace('5Cu', '%u')


async def get_info_from_query_url(query_url, stationName, date, from_station, to_station):
    cookie1 = get_part_cookie()
    cookie2 = get_another_cookie(stationName, date, from_station, to_station)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/61.0.3163.100 Safari/537.36",
        "Cookie": cookie1 + cookie2
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(query_url, headers=headers) as resp:
            info = await resp.json()  # 获取所有车次信息
            all_trains = info['data']['result']  # 获取所有车次信息
            for one_train in all_trains:  # 遍历取出每辆车的信息
                data_list = one_train.split('|')
                train_number = data_list[3]  # 车次
                from_station_code = data_list[6]  # 出发站代号
                from_station_name = '上海'  # 出发站名称
                to_station_code = data_list[7]  # 到达站代号
                to_station_name = '北京'  # 到达站名称
                go_time = data_list[8]  # 出发时间
                arrive_time = data_list[9]  # 到达时间
                cost_time = data_list[10]  # 历时
                special_class_seat = data_list[32] or '--'  # 商务/特等座
                first_class_seat = data_list[31] or '--'  # 一等座
                second_class_seat = data_list[30] or '--'  # 二等座
                soft_sleep = data_list[23] or '--'  # 软卧
                hard_sleep = data_list[28] or '--'  # 硬卧
                hard_seat = data_list[29] or '--'  # 硬座
                no_seat = data_list[26] or '--'  # 无座
                print(train_number, from_station_code, from_station_name, to_station_code, to_station_name, go_time,
                      arrive_time, cost_time, special_class_seat, first_class_seat, second_class_seat, soft_sleep,
                      hard_sleep, hard_seat, no_seat)
    #             # TODO:写入数据库或文件


# 主程序
async def main():
    # 初始化
    global tasks
    init()

    stationName, stationCode = get_all_station_name_and_code()
    query_url = get_query_url(stationName, '2022-07-14', '上海', '北京')
    tasks = [asyncio.create_task(get_info_from_query_url(query_url, stationName, '2022-07-14', '上海', '北京'))]
    # TODO：循环，自己改即可

    # for from_station in stationName:
    #     for to_station in stationName:
    #         if from_station != to_station:
    #             for i in range(1, 30):
    #                 query_url = get_query_url(stationName, '2022-07-14', from_station, to_station)
    #                 tasks = [asyncio.create_task(get_info_from_query_url(
    #                     query_url, stationName, '2022-07-14', from_station, to_station))]

    await asyncio.wait(tasks)


# 程序入口
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
