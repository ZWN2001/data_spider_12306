import asyncio
import re

import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import aiohttp
from time import sleep


#
# # 初始化
# def init():
#     # TODO：后期换成无头浏览器
#     option = Options()
#     option.add_argument('--disable-blink-features=AutomationControlled')
#     # 定义为全局变量，方便其他模块使用
#     global url, browser, username, password, wait, proxy
#     proxy = {'https': '127.0.0.1:7890'}
#     # 登录界面的url
#     url = 'https://kyfw.12306.cn/otn/resources/login.html'
#     # 实例化一个chrome浏览器
#     browser = webdriver.Chrome(options=option)
#     # 用户名
#     username = '2134356214@qq.com'
#     # 密码
#     password = '-'
#     # 设置等待超时
#     wait = WebDriverWait(browser, 20)


# # 登录
# def login():
#     # 打开登录页面
#     browser.get(url)
#     # 获取用户名输入框
#     user = wait.until(EC.presence_of_element_located((By.ID, 'J-userName')))
#     # 获取密码输入框
#     passwd = wait.until(EC.presence_of_element_located((By.ID, 'J-password')))
#     # 输入用户名
#     user.send_keys(username)
#     # 输入密码
#     passwd.send_keys(password)
#
#     browser.find_element(By.ID, "J-login").click()
#
#
# # 模拟拖动
# def move_to_gap():
#     # 得到滑块标签
#     slider = wait.until(EC.presence_of_element_located((By.ID, 'nc_1_n1z')))
#     ActionChains(browser).drag_and_drop_by_offset(slider, 300, 0).perform()


def get_all_station_name_and_code():
    station_name_source = requests.get(
        ' https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9235')
    pattern = r'([\u4e00-\u9fa5]+)\|([A-Z]+)'  # 正则匹配规则
    result = re.findall(pattern, station_name_source.text)
    stationName = dict(result)  # 所有车站信息，转换为字典
    stationCode = dict(zip(stationName.values(), stationName.keys()))
    return stationName, stationCode


def get_query_url(text, date, from_station, to_station):
    # 构建用于查询列车车次信息的url
    # 参数：日期，出发地，到达地
    # key为车站名称， value为车站代号

    date = date
    from_station = text[from_station]
    to_station = text[to_station]
    print([from_station, to_station])
    # 构造直接获取车次信息的url
    query_url = ("https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={}"
                 "&leftTicketDTO.from_station={}"
                 "&leftTicketDTO.to_station={}"
                 "&purpose_codes=ADULT"
                 ).format(date, from_station, to_station)
    print(query_url)
    return query_url


async def get_info_from_query_url(query_url):
    cookie = "tk=YdFLdVKmaySrnWBxT8QCfZ6RA5Vf5k-rbcS1S0; JSESSIONID=8082F95D9CBF715F28E0AFC924BB051F; RAIL_EXPIRATION=1657682972442; RAIL_DEVICEID=e8EMu5K2CHTHt8PLHUia5L5Ibu_lWeVTFaIitxQ1UkZ4eDZgX81p0Li5JVD47mYGJVHxU69VVUz1TnLdd2pL3imK2IcLnGDrYpw02-Xjl_jrJaJ6sMqkg4Fp2EaearN9UgJbAWPH2ey1xUlH9qoJCNyafVPSOVIo; guidesStatus=off; highContrastMode=defaltMode; cursorStatus=off; BIGipServerpool_passport=199492106.50215.0000; route=c5c62a339e7744272a54643b3be5bf64; BIGipServerpassport=870842634.50215.0000; current_captcha_type=Z; _jc_save_toStation=%u5317%u4EAC%2CBJP; fo=lychk6583r3ve8grL4FA6lRnmc8pYiQJMzoIogEpjAN+Wvf8KuYinWwvkuxL4RsfXlPqgmgO9tBrFErdJPOC9Cs6fybJyq58xTqFtFPdq4FBlLYXuWlpHqhAb5a8HF14gT9cv9l/VUxwkU8dH/32DQ9ngCzjAo/RBUAbfKByRlUVXbhfH2hZKbtse9c%3D; _jc_save_fromDate=2022-07-14; _jc_save_wfdc_flag=dc; _jc_save_toDate=2022-07-10; _jc_save_fromStation=%u4E0A%u6D77%2CSHH; BIGipServerportal=2949906698.17695.0000; BIGipServerotn=568852746.24610.0000; uKey=8b53fb39e2c3d400819319fc95e08e017b875d866168a46db8e3dc78eb3a32c8"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
        "Cookie": cookie
    }
    proxies = {
        "HTTP": "http://182.34.27.89:9999"
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
                # TODO:写入数据库或文件


# 主程序
async def main():
    # # 初始化
    # init()
    # # 登录
    # login()
    # sleep(2)
    # # 移动滑块
    # move_to_gap()
    # sleep(2)
    stationName, stationCode = get_all_station_name_and_code()
    query_url = get_query_url(stationName, '2022-07-14', '上海', '北京')
    tasks = [asyncio.create_task(get_info_from_query_url(query_url))]
    await asyncio.wait(tasks)
    # get_info_from_query_url(query_url)


# 程序入口
if __name__ == '__main__':
    # main()
    # asyncio.run(main())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
