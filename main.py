from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from time import sleep


# 初始化
def init():
    option = Options()
    option.add_argument('--disable-blink-features=AutomationControlled')
    # 定义为全局变量，方便其他模块使用
    global url, browser, username, password, wait
    # 登录界面的url
    url = 'https://kyfw.12306.cn/otn/resources/login.html'
    # 实例化一个chrome浏览器
    browser = webdriver.Chrome(options=option)
    # 用户名
    username = '2134356214@qq.com'
    # 密码
    password = 'ZWN370782'
    # 设置等待超时
    wait = WebDriverWait(browser, 20)


# 登录
def login():
    # 打开登录页面
    browser.get(url)
    # 获取用户名输入框
    user = wait.until(EC.presence_of_element_located((By.ID, 'J-userName')))
    # 获取密码输入框
    passwd = wait.until(EC.presence_of_element_located((By.ID, 'J-password')))
    # 输入用户名
    user.send_keys(username)
    # 输入密码
    passwd.send_keys(password)

    browser.find_element(By.ID, "J-login").click()


# 模拟拖动
def move_to_gap():
    # 得到滑块标签
    slider = wait.until(EC.presence_of_element_located((By.ID, 'nc_1_n1z')))
    ActionChains(browser).drag_and_drop_by_offset(slider, 300, 0).perform()


# 主程序
def main():
    # 初始化
    init()
    # 登录
    login()
    # # 移动滑块
    move_to_gap()
    sleep(5)


# 程序入口
if __name__ == '__main__':
    main()
