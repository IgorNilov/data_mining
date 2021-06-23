# Подключение библиотек
import time
import json
from pathlib import Path
import requests


# Создаем класс Parse5ka нашего парсера сайта
class Parse5ka:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0)"
        " Gecko/20100101 Firefox/88.0"
    }

    # Перегружаем init, передаем значение старта url
    # и указываем путь сохранения файлов
    def __init__(self, start_url: str, save_dir: Path):
        self.start_url = start_url
        self.save_dir = save_dir

    # создаем метод _get_response = бесконечный цикл
    # если код ответа 200 то возвращает return response
    # если нет то запрос повториться через time.sleep(0.2)
    def _get_response(self, url: str) -> requests.Response:
        while True:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response
            time.sleep(0.2)

    # точка запуска (старта) внешний интерфейс
    # цикл
    def run(self):
        for product in self._parse(self.start_url):
            file_name = f"{product['id']}.json"
            file_path = self.save_dir.joinpath(file_name)
            self._save(product, file_path)

    # метод _parse (генератор)
    # работает переходит по (ссылке на страницу товаров) self._get_response(url)
    # собирает все товары со страницы yield product и сохраняет for product in data["results"]
    # работает пока не закончатся все ссылки на страницы и товары в них
    def _parse(self, url):
        while url:
            response = self._get_response(url)
            data = response.json()
            url = data["next"]
            for product in data["results"]:
                yield product

    #  метод _save сохранение данные ввиде словаря data: dict и путь file_path
    @staticmethod
    def _save(data: dict, file_path):
        jdata = json.dumps(data, ensure_ascii=False)
        file_path.write_text(jdata, encoding="UTF-8")


"""
 новый класс наследованный от парсера
 в него передаются новые categories_url каталога товаров
"""


class CategoriesParser(Parse5ka):
    def __init__(self, categories_url, *args, **kwargs):
        self.categories_url = categories_url
        super().__init__(*args, **kwargs)

    # метод получает список категорий
    def _get_categories(self):
        response = self._get_response(self.categories_url)
        data = response.json()
        return data

    def run(self):
        for category in self._get_categories():
            category["products"] = []
            params = f"?categories={category['parent_group_code']}"
            url = f"{self.start_url}{params}"

            category["products"].extend(list(self._parse(url)))
            file_name = f"{category['parent_group_name']}.json"
            cat_path = self.save_dir.joinpath(file_name)
            self._save(category, cat_path)


# функция для создания директории если ее нет то создает
def get_dir_path(dir_name: str) -> Path:
    dir_path = Path(__file__).parent.joinpath(dir_name)
    if not dir_path.exists():
        dir_path.mkdir()
    return dir_path


if __name__ == "__main__":
    url = "https://5ka.ru/api/v2/special_offers/"
    category_url = "https://5ka.ru/api/v2/categories/"
    product_path = get_dir_path("products")
    parser = Parse5ka(url, product_path)
    category_parser = CategoriesParser(category_url, url, get_dir_path("category_products"))
    category_parser.run()
