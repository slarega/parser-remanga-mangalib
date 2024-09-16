import re
import time
from pandas import DataFrame
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains


class ParserRemanga:
    bookmarks_dict = {}
    bookmarks_ignored = ['Буду читать', 'Не интересно']  # игнорируемые закладки
    total_title_num = 0

    def __init__(self, driver: uc.Chrome):
        self.driver = driver

    def auth(self):
        """
        Авторизация Remanga
        """
        self.driver.get('https://remanga.org/user/bookmarks')
        self.driver.switch_to.window(self.driver.window_handles[0])
        time.sleep(1)
        try:
            self.driver.find_element(By.XPATH, '//span[text()="Через Google"]').click()
            time.sleep(1)
        except NoSuchElementException:
            return

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
            'id закладки': [название, кол-во тайтлов, кол-во скроллов]
        """
        self.total_title_num = 0
        self.driver.get('https://remanga.org/user/bookmarks?type=0')
        time.sleep(1)
        soup = self.get_soup()
        full_bookmarks = soup.findAll('button',
                                      {'class': 'Button_button___CisL Tab_root__Slu9a Tab_textColor-primary__Iqa3H'})
        del full_bookmarks[-1]

        for bookmark in full_bookmarks:
            data = re.split(r'(\d+)', bookmark.text)
            data[0] = data[0].strip()
            if data[0] not in self.bookmarks_ignored:
                def_title_num = len(soup.findAll('div', {'class': 'Grid_gridItem__aPUx1 p-1'})) // 2
                scroll = int(data[1]) // def_title_num
                self.bookmarks_dict[bookmark.get('data-value')] = [data[0], int(data[1]), scroll]
        self.total_title()

    def total_title(self):
        """
        Суммарное количество тайтлов
        """
        self.total_title_num = 0
        for i in self.bookmarks_dict.values():
            self.total_title_num += i[1]

    def get_title_data(self, url: str) -> [str]:
        """
        Получение данных тайтла по url
        """
        self.driver.get(f'https://remanga.org{url}')  # тайтл
        time.sleep(2)
        # данные
        soup = self.get_soup()
        names = soup.find('p', attrs={'itemprop': 'alternativeHeadline'}).text.split('/')
        names = [name.rstrip().lstrip() for name in names]
        name_ru = soup.find('h1').contents[0]
        name_eng = names[0]
        alter_names = ";".join(str(element) for element in names[1:])
        title_type = soup.find('h5').contents[0].split()[0]

        return [name_ru, name_eng, title_type, alter_names]

    def parse_to_excel(self) -> str:
        """
        Запись информации по тайтлам в excel
        """
        df1 = DataFrame(columns=['Name_ru', 'Name_eng', 'Type', 'Alternative_names'])

        title_num = 1
        for bookmark_id, value in self.bookmarks_dict.items():
            self.driver.get(f'https://remanga.org/user/bookmarks?type={bookmark_id}')  # сайт закладки
            time.sleep(1)
            # переход к нижней части страницы
            scrolls = 0
            while scrolls < value[2]:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                scrolls += 1

            title_blocks = self.get_soup().findAll('div', {'class': 'Grid_gridItem__aPUx1 p-1'})
            for block in title_blocks:
                url = block.find('a')['href']
                df1.loc[len(df1)] = self.get_title_data(url)

                # очистка кэша
                if title_num % 30 == 0: self.delete_cache()
                title_num += 1

        df1.to_excel('parse-data/parse_remanga.xlsx', index=False)
        return f'Remanga: получены данные {len(df1.index)} тайлтлов из {self.total_title_num}'

    def start(self):
        self.auth()
        self.update_dict()
        result = self.parse_to_excel()
        return result
