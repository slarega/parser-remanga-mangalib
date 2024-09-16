import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

load_dotenv()


def Create_Chrome() -> uc.Chrome:
    """
    Браузер + авторизация
    :return uc.Chrome:
    """
    email = os.environ.get('GOOGLE_LOG')
    password = os.environ.get('GOOGLE_PASS')

    options = uc.ChromeOptions()  # запуск Chrome
    options.page_load_strategy = 'none'
    driver = uc.Chrome(options=options)

    driver.get('https://accounts.google.com/')
    time.sleep(4)
    driver.find_element(By.XPATH, '//*[@id="identifierId"]').send_keys(email)
    time.sleep(2)
    driver.find_element(By.XPATH, '//*[@id="identifierNext"]/div/button/span').click()
    time.sleep(10)
    driver.find_element(By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input').send_keys(password)
    time.sleep(2)
    driver.find_element(By.XPATH, '//*[@id="passwordNext"]/div/button/span').click()

    return driver
