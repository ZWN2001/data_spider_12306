import re
import datetime
import urllib.parse
from time import sleep

import pymysql
import requests

global browser, wait, tasks, db, cursor, sql_get_code, train_route_id


def init():
    # 初始化
    global tasks, cursor, db, sql_get_code
    db = pymysql.connect(host='localhost',
                         user='root',
                         password='123456',
                         database='train_12306')
    cursor = db.cursor()
    tasks = []
    sql_get_code = "SELECT station_id FROM station WHERE station_name = %s"


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


# def write_all_station_name_and_code_to_db(stationName):
#     for sn in stationName.keys():
#         city = sn
#         # 通过站名获取城市名
#         if sn[-1:] in ("东", "西", "南", "北"):
#             city = sn[0:-1]
#         sql = "INSERT INTO station VALUES (%s, %s, %s) "
#         cursor.execute(sql, (stationName[sn], sn, city))
#     try:
#         db.commit()  # 所有sql一起提交以提高效率
#     except:
#         # 发生错误时回滚
#         db.rollback()


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


def save_station_start_to_end(train_node, train_route_id, elapsed_time_minute):
    sql_insert_train_route = "INSERT INTO train_route VALUES (%s, %s, %s, %s, %s) "

    start_station_name = train_node["start_station_name"]
    end_station_name = train_node["end_station_name"]
    cursor.execute(sql_get_code, start_station_name)
    results = cursor.fetchall()
    start_station_code = results[0][0]
    cursor.execute(sql_get_code, end_station_name)
    results = cursor.fetchall()
    end_station_code = results[0][0]
    start_time = train_node["start_time"]
    cursor.execute(sql_insert_train_route,
                   (train_route_id, start_station_code, end_station_code, start_time, elapsed_time_minute))


def get_info_from_query_url(query_url, stationName, date, from_station, to_station, catch):
    global train_route_id
    sql_insert_train_route_atom = "INSERT INTO train_route_atom VALUES (%s, %s, %s, %s, %s, %s) "
    # TODO：建议换用自己的cookie，否则不保证cookie过期而导致的问题，或者使用main2.py,自动获取token
    cookie1 = "JSESSIONID=824E6B2E5616FB0D8F04EE0A68672401; tk=qVvmfB1mFvJdVLZ8S7XhJHwFvtZhLK9vxhS1S0; " \
              "guidesStatus=off; RAIL_EXPIRATION=1658478690426; " \
              "RAIL_DEVICEID=fMtfQqqXa7sE9TyPVsJKIcM2p4wt95NAP_p5yNbudyiVftKEuq7Ufg30PsHGn16Bo1we_DgYBp31_SC4gy-UeII" \
              "-nQbHfRc_u78XgTD37j_SiINpRzkGbpyuZduEXnZ47W86o-sWhwJy8JpYfIyTuEXQvXLTXNES;  " \
              "BIGipServerotn=938476042.24610.0000; highContrastMode=defaltMode; cursorStatus=off; " \
              "BIGipServerpool_passport=233046538.50215.0000; route=c5c62a339e7744272a54643b3be5bf64; " \
              "uKey=bcffa7070b0e61fc1719135aef7a60d454d3fbee33ec2870003ad8507f88c024; current_captcha_type=Z; "
    cookie2 = get_another_cookie(stationName, date, from_station, to_station)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/61.0.3163.100 Safari/537.36",
        "Cookie": cookie1 + cookie2
    }
    resp = requests.get(query_url, headers=headers)
    info = resp.json()  # 获取所有车次信息
    all_trains = info['data']['result']  # 获取所有车次信息
    for one_train in all_trains:  # 遍历取出每辆车的信息
        data_list = one_train.split('|')
        train_no = data_list[2]
        train_number = data_list[3]  # 车次
        from_station_code = data_list[6]  # 出发站代号
        to_station_code = data_list[7]  # 到达站代号
        all_time = data_list[10]  # 总时间

        if train_number not in catch:
            catch.append(train_number)
            print(train_number)
            detail_url = ("https://kyfw.12306.cn/otn/czxx/queryByTrainNo?"
                          "train_no={}"
                          "&from_station_telecode={}"
                          "&to_station_telecode={}"
                          "&depart_date={}").format(train_no, from_station_code, to_station_code, str(date))

            resp_detail = requests.get(detail_url)
            node_info = resp_detail.json()

            train_nodes = node_info['data']['data']

            times = all_time.split(":")
            all_time = int(times[0]) * 60 + int(times[1])  # 总耗时
            for train_node in train_nodes:
                station_name = train_node["station_name"]
                cursor.execute(sql_get_code, station_name)
                results = cursor.fetchall()
                station_id = results[0][0]
                train_route_id = train_number
                station_no = train_node["station_no"]
                arrive_time = train_node["arrive_time"]
                start_time = train_node["start_time"]
                stopover_time = train_node["stopover_time"]

                try:
                    cursor.execute(sql_insert_train_route_atom, (train_route_id, station_id, station_no, arrive_time,
                                                                 start_time, stopover_time))
                except:
                    pass

            save_station_start_to_end(train_nodes[0], train_route_id, all_time)
            db.commit()


# 主程序
def main():
    global tasks
    stationName, stationCode = get_all_station_name_and_code()
    # write_all_station_name_and_code_to_db(stationName)

    date_object = datetime.date(2022, 8, 3)
    target_stations = ["天津", "北京", "上海", "重庆", "长沙", "长春", "成都",
                       "福州", "广州", "贵阳", "呼和浩特", "哈尔滨", "合肥", "杭州",
                       "海口", "济南", "昆明", "兰州", "南宁", "南京",
                       "南昌", "沈阳", "石家庄", "太原", "武汉", "西宁",
                       "西安", "银川", "郑州", "深圳", "厦门", "无锡", "苏州", "常州",
                       "宁波", "南通", "青岛", "泉州", "佛山", "东莞"]
    # target_stations = ["天津", "北京"]
    catch = []
    for from_station in target_stations:
        for to_station in target_stations:
            if from_station != to_station:
                sleep(2)
                print(from_station, to_station)
                query_url = get_query_url(stationName, date_object, from_station, to_station)
                get_info_from_query_url(query_url, stationName, date_object, from_station, to_station, catch)

    db.close()


# 程序入口
if __name__ == '__main__':
    init()
    main()
