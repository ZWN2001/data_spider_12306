import asyncio
import re
import datetime
import urllib.parse
from time import sleep

import pymysql
import requests
import aiohttp

global browser, wait, tasks, db, client


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


def write_all_station_name_and_code_to_db(stationName):
    cursor = db.cursor()
    for sn in stationName.keys():
        city = sn
        if sn[-1:] in ("东", "西", "南", "北") and len(city) > 2:
            city = sn[0:-1]
        sql = "INSERT INTO station VALUES (%s, %s, %s) "
        if len(city) > 1:
            cursor.execute(sql, (stationName[sn], sn, city))

    try:
        db.commit()  # 所有sql一起提交以提高效率
    except:
        # 发生错误时回滚
        db.rollback()

    # 关闭数据库连接
    db.close()


# 构建用于查询列车车次信息的url
def get_query_url(stationName, date, from_station, to_station):
    # key为车站名称， value为车站代号
    from_station = stationName[from_station]
    to_station = stationName[to_station]
    # 构造直接获取车次信息的url
    query_url = ("https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={}"
                 "&leftTicketDTO.from_station={}"
                 "&leftTicketDTO.to_station={}"
                 "&purpose_codes=0X00"
                 ).format(date, from_station, to_station)
    return query_url


def escape(data):
    fill = re.findall(r'[\u4e00-\u9fa5]', data)
    if len(fill) > 0:
        for ch in fill:
            data = data.replace(ch, '5Cu{0}'.format(hex(ord(ch))[2:].upper()))
    return urllib.parse.quote(data.encode('unicode-escape'), safe='*@-_+./').replace('5Cu', '%u')


async def get_info_from_query_url(query_url, stationName, date, from_station, to_station, catch, cursor):
    sql = "INSERT INTO train_route VALUES (%s, %s, %s, %s) "
    # TODO：建议换用自己的cookie，否则不保证cookie过期而导致的问题，或者使用main2.py,自动获取token
    cookie1 = "JSESSIONID=6C15081C8C2298D4003F1A17806428A0; tk=E2zTT5p5Cfg7Uha0fWmX-sj1Ik4kYzsg27S1S0; guidesStatus=off; highContrastMode=defaltMode; cursorStatus=off; fo=lychk6583r3ve8grL4FA6lRnmc8pYiQJMzoIogEpjAN+Wvf8KuYinWwvkuxL4RsfXlPqgmgO9tBrFErdJPOC9Cs6fybJyq58xTqFtFPdq4FBlLYXuWlpHqhAb5a8HF14gT9cv9l/VUxwkU8dH/32DQ9ngCzjAo/RBUAbfKByRlUVXbhfH2hZKbtse9c%3D;  BIGipServerotn=1072693770.38945.0000; BIGipServerpool_passport=283378186.50215.0000; RAIL_EXPIRATION=1658141541162; RAIL_DEVICEID=imvIBxu2tpyGT6uOFVNQ_7V0aWLZNkjJ8p2mdZQkq2kkKhHCX7KQo4ZUuDP-j8lEMK754pWISeD6bLke46xY33I4M8KCSCOOmfwWy_-LGSQBHUeHMqXEHv_ZvZOiUm9vTh3Z30IcfAVChEVKm21F6_36N5HRFQna; route=9036359bb8a8a461c164a04f8f50b252; uKey=476a47c3fdd124b23cf1378176af7c94ebbe7823bd6897fded2e78a14b54bab3; current_captcha_type=Z;"
    cookie2 = get_another_cookie(stationName, date, from_station, to_station)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/61.0.3163.100 Safari/537.36",
        "Cookie": cookie1 + cookie2
    }

    async with client.get(query_url, headers=headers) as resp:
            info = await resp.json()  # 获取所有车次信息
            all_trains = info['data']['result']  # 获取所有车次信息
            for one_train in all_trains:  # 遍历取出每辆车的信息
                data_list = one_train.split('|')
                train_number = data_list[3]  # 车次
                from_station_code = data_list[6]  # 出发站代号
                from_station_name = from_station  # 出发站名称
                to_station_code = data_list[7]  # 到达站代号
                to_station_name = to_station  # 到达站名称
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
                # TODO:写入数据库或文件
                # if train_number not in catch:  # 缓存以去重
                #     times = cost_time.split(":")
                #     time = int(times[0]) * 60 + int(times[1])
                #     cursor.execute(sql, (train_number, from_station_code, to_station_code, time))
                #     try:
                #         db.commit()
                #     except:
                #         # 发生错误时回滚
                #         db.rollback()
                #     catch.append(train_number)
    sleep(3)


# 主程序
async def main():
    # 初始化
    global tasks, client
    client = aiohttp.ClientSession()
    cursor = db.cursor()
    tasks = []

    stationName, stationCode = get_all_station_name_and_code()
    write_all_station_name_and_code_to_db(stationName)
    catch = []
    date_object = datetime.date(2022, 8, 3)
    query_url = get_query_url(stationName, date_object, '天津', '北京')
    tasks = [
        asyncio.create_task(get_info_from_query_url(query_url, stationName, date_object, '天津', '北京', catch, cursor))]

    # # # TODO：循环，自己改即可
    # for from_station in stationName.keys():
    #     for to_station in stationName.keys():
    #         if from_station != to_station:
    #             catch = []
    #             for i in range(1, 3):
    #                 date_object = datetime.date(2022, 8, i)
    #                 query_url = get_query_url(stationName, date_object, from_station, to_station)
    #                 tasks.append(asyncio.create_task(get_info_from_query_url(
    #                     query_url, stationName, date_object, from_station, to_station, catch, cursor)))

    await asyncio.wait(tasks)
    cursor.close()


# 程序入口
if __name__ == '__main__':
    db = pymysql.connect(host='localhost',
                         user='root',
                         password='123456',
                         database='train_12306')  # TODO:你的数据库信息
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_until_complete(client.close())
    loop.run_until_complete(asyncio.sleep(10))
    loop.close()
    db.close()
