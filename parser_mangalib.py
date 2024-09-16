import os
import re
import time
from pandas import DataFrame
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv  # python-dotenv

load_dotenv()

mangalib_id = os.environ.get('MANGALIB_ID')
bookmark_title_class = os.environ.get('BOOKMARK_TITLE_CLASS')
bookmark_title_added = os.environ.get('BOOKMARK_TITLE_ADDED')
title_data_class = os.environ.get('TITLE_DATA_CLASS')


class ParserMangalib:
    bookmarks_dict = {}
    total_title_num = 0

    def __init__(self, driver: uc.Chrome):
        self.driver = driver

    def auth(self):
        """
        Авторизация Mangalib
        """
        self.driver.get('https://test-front.mangalib.me/ru')
        time.sleep(5)

        try:
            self.driver.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[1]/div/div[3]/div[1]/a').click()
        except NoSuchElementException:
            return

        time.sleep(3)

        try:
            self.driver.find_element(By.XPATH, '/html/body/div/div[1]/div[2]/div[2]/div[2]/a[4]').click()  # google
            time.sleep(2)
        except NoSuchElementException:
            pass

        self.driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div[2]/form[1]/button').click()  # продолжить как

    def delete_cache(self):
        """
        Очистка кэша driver
        """
        self.driver.switch_to.new_window()  # открываем новую вкладку
        self.driver.get('chrome://settings/clearBrowserData')  # Открываем настройки chrome
        time.sleep(0.2)
        actions = ActionChains(self.driver)
        actions.key_down(Keys.SHIFT).send_keys(Keys.TAB * 6).key_up(Keys.SHIFT)  # select "all time" browsing data
        actions.send_keys(Keys.DOWN * 5 + Keys.TAB * 7 + Keys.ENTER)  # click on "clear data" button
        time.sleep(0.2)
        self.driver.close()  # закрываем новую вкладку
        self.driver.switch_to.window(self.driver.window_handles[0])  # возвращаемся на исходную вкладку

    def get_soup(self):
        return BeautifulSoup(self.driver.page_source, 'html.parser')

    def update_dict(self):
        """
        Заполняет bookmarks_dict, где:
            'название закладки': [кол-во тайтлов, кол-во скроллов]
        """
        self.driver.get(f'https://test-front.mangalib.me/ru/user/{mangalib_id}')
        time.sleep(2)
        full_bookmarks = self.get_soup().findAll('div', {'class': 'menu-item'})
        del full_bookmarks[0]  # закладка 'Все'

        for bookmark in full_bookmarks:
            data = re.split(r'(\d+)', bookmark.text)
            if len(data) == 3:
                self.bookmarks_dict[data[0]] = [int(data[1]), int(data[1]) // 15 + 2]
        del self.bookmarks_dict['В планах']  # закладка 'В планах'
        self.total_title()

    def total_title(self):
        """
        Суммарное количество тайтлов
        """
        self.total_title_num = 0
        for i in self.bookmarks_dict.values():
            self.total_title_num += i[0]

    def get_title_data(self, url: str, added: str) -> [str]:
        """
        Получение данных тайтла по url
        """
        self.driver.switch_to.new_window()
        self.driver.get(url)
        time.sleep(2)

        if self.get_soup().find('div', {'class': 'popup-body'}):
            self.driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div[2]/div[2]/label/span[1]').click()
            self.driver.find_element(By.XPATH, '//button[normalize-space()="Продолжить"]').click()

        try:
            self.driver.find_element(By.XPATH, '//button[normalize-space()="Показать ещё..."]').click()
        except NoSuchElementException:
            pass

        try:
            _ = self.get_soup().find('h1').text
        except:
            time.sleep(13)
            self.driver.refresh()
            time.sleep(2)

        time.sleep(0.5)
        # данные
        soup = self.get_soup()
        name_ru = soup.find('h1').text
        name_eng = soup.find('h2').text
        data = soup.findAll('div', {'class': f'{title_data_class}'})
        title_type = data[0].text
        alter_names = ', '.join(x for x in [i.text for i in data[-1].findAll('span')])

        self.driver.close()  # закрываем новую вкладку
        self.driver.switch_to.window(self.driver.window_handles[0])  # возвращаемся на исходную вкладку
        time.sleep(0.2)
        return [name_ru, name_eng, title_type, added, alter_names]

    def parse_to_excel(self) -> str:
        """
        Запись информации по тайтлам в excel
        """
        df1 = DataFrame(columns=['Name_ru', 'Name_eng', 'Type', 'Date_added', 'Alternative_names'])
        title_num = 1
        self.driver.get(f'https://test-front.mangalib.me/ru/user/{mangalib_id}')  # профиль
        time.sleep(2)

        for bookmark, item in self.bookmarks_dict.items():
            try:
                self.driver.find_element(By.XPATH, f"//*[text()='{bookmark}']").click()  # сайт закладки
                time.sleep(1)
                self.driver.find_element(By.XPATH, f"//*[text()='{bookmark}']").click()

            except NoSuchElementException:
                self.driver.refresh()
                time.sleep(2)
                self.driver.find_element(By.XPATH, f"//*[text()='{bookmark}']").click()
                time.sleep(0.5)

            # переход к нижней части страницы
            scrolls = 0
            while scrolls < item[1]:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                scrolls += 1
            time.sleep(0.2)

            # данные
            location_blocks = self.get_soup().findAll('div', {'class': f'{bookmark_title_class}'})
            for block in location_blocks:
                url = ('https://test-front.mangalib.me' + block.find('a')['href'].split('=')[0])
                added = block.find('div', {'class': f'{bookmark_title_added}'}).text.split()[1]
                df1.loc[len(df1)] = self.get_title_data(url, added)
                time.sleep(0.2)
                # очистка кэша
                if title_num % 20 == 0:
                    self.delete_cache()
                title_num += 1

        df1.to_excel('parse-data/parse_mangalib.xlsx', index=False)
        return f'Mangalib: получены данные {len(df1.index)} тайлтлов из {self.total_title_num}'

    def start(self) -> str:
        """
        Парсим данные
        """
        self.update_dict()
        time.sleep(1)
        result = self.parse_to_excel()
        return result
