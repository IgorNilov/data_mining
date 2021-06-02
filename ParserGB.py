import typing
import time
import requests
from urllib.parse import urljoin
import bs4
import pymongo

"""
1. Открыть точку входа
2. Скопировать список ссылок на статьи (вытеснение)
3. Перейти/ Открыть ссылку на статью из списка
4. Извлечь информацию в соответствии с требованиями
5. Сохранить информацию в БД
6. Перейти к шагу 3, со следующей ссылкой (повторяем пока не закончатся)
7. Переход к шагу 1 с точкой входа следующей странички пагинации (повтор пока не закончаться)

"""
"""
Пагинируемые странички
1. Извлечь ссылки на статьи
1.1 Породить в очереди задач => задачи
2. Извлечь ссылки пагинации 
2.1 Породить в очереди задач => задачи
"""
"""
Страница поста
Составить структуру информации (извлечь данные)
Сохранить структуру данных

"""


class GbBlogParse:
    headers = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0'
    }
    __parse_time = 0

    def __init__(self, start_url, db, delay=1.0):
        self.start_url = start_url  # стартовый url
        self.db = db
        self.delay = delay
        self.done_url = set()  # список хранения отработанных url, словарь отработанных url
        self.tasks = []  # список задач
        self.task_creator({self.start_url, }, self.parse_feed)  # создаем первую tasks на старте

    def _get_response(self, url):  # метод запроса (_get_response) с контролем времени
        while True:
            next_time = self.__parse_time + self.delay
            if next_time > time.time():
                time.sleep(next_time - time.time())
            response = requests.get(url, headers=self.headers)
            print(f"RESPONSE: {response.url}")
            self.__parse_time = time.time()
            if response.status_code == 200:
                return response

    def get_task(self, url: str, callback: typing.Callable) -> typing.Callable:  # хранение Callable объектов
        def task():
            response = self._get_response(url)
            return callback(response)

        return task

    def run(self):  # функция запуска контроль очереди
        while True:
            try:
                task = self.tasks.pop(0)  # удаляет объект из списка и возвращает его
                task()
            except IndexError:  # если возникнет ошибка
                break

    def task_creator(self, urls: set, callback):  # постановка задач
        urls_set = urls - self.done_url  # убираем url тех страниц где уже были
        for url in urls_set:
            self.tasks.append(self.get_task(url, callback))
            self.done_url.add(url)

    def parse_feed(self, response: requests.Response):  # метод пагинируемых страничек
        soup = bs4.BeautifulSoup(response.text, "lxml")
        ul_pagination = soup.find("ul", attrs={"class": "gb__pagination"})  # ищем ul = "class": "gb__pagination"
        self.task_creator(
            {
                urljoin(response.url, a_tag.attrs["href"])  # поиск уникальных ссылок url пагтнации
                for a_tag in ul_pagination.find_all("a")
                if a_tag.attrs.get("href")
            },
            self.parse_feed,  # добавляет task = parse_feed в орчередь
        )
        post_wrapper = soup.find("div", attrs={"class": "post-items-wrapper"})  # поиск постов
        self.task_creator(
            {
                urljoin(response.url, a_tag.attrs["href"])
                for a_tag in post_wrapper.find_all("a", attrs={"class": "post-item__title"})
                if a_tag.attrs.get("href")
            },
            self.parse_post,  # добавляет task = parse_post в орчередь
        )

    def parse_post(self, response: requests.Response):  # метод пост (сбор данных поста)
        soup = bs4.BeautifulSoup(response.text, 'lxml')
        author_name_tag = soup.find('div', attrs={"itemprop": "author"})
        data = {
            "post_data": {  # данные поста
                "title": soup.find("h1", attrs={"class": "blogpost-title"}).text,
                "url": response.url,
                "id": soup.find("comments").attrs.get("commentable-id"),
            },
            "author_data": {  # данные автора поста
                "url": urljoin(response.url, author_name_tag.parent.attrs.get("href")),
                "name": author_name_tag.text,
            },
            "tags_data": [  # данные поста
                {"name": tag.text, "url": urljoin(response.url, tag.attrs.get("href"))}
                for tag in soup.find_all("a", attrs={"class": "small"})
            ],
            "comments_data": self._get_comments(soup.find("comments").attrs.get("commentable-id")),
        }
        self._save(data)  # сохранение данных поста

    def _get_comments(self, post_id):
        api_path = f"/api/v2/comments?commentable_type=Post&commentable_id={post_id}&order=desc"
        response = self._get_response(urljoin(self.start_url, api_path))
        data = response.json()
        return data

    def _save(self, data: dict):  # метод сохранения
        collection = self.db["gb_parse_geekbrains"]["gb_parse"]  # сохраняет в БД
        collection.insert_one(data)


if __name__ == '__main__':
    client_db = pymongo.MongoClient("mongodb://localhost:27017")  # клиент который взаимодействует с сервером
    # если удаленный сервер применяется шаблон
    # client_db = pymongo.MongoClient("mongodb://user:password@localhost:27017/ dbname")
    # user:password(имя пользователя и пароль)
    # localhost(доменное имя или IP):27017(порт)
    # dbname(имя БД)")
    parser = GbBlogParse("https://gb.ru/posts", client_db, )
    parser.run()
