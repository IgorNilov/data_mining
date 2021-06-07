import typing
import requests
from urllib.parse import urljoin
import bs4
import time
import pymongo
from database.database import Database


class GbBlogParse:
    headers = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0'
    }
    __parse_time = 0

    def __init__(self, start_url, db: Database, delay=1.0):
        self.start_url = start_url
        self.db = db
        self.delay = delay
        self.done_url: typing.Set[str] = set()
        self.tasks: typing.List[typing.Callable] = []
        self.task_creator({self.start_url,}, self.parse_feed)

    def _get_response(self, url):
        while True:
            next_time = self.__parse_time + self.delay
            if next_time > time.time():
                time.sleep(next_time - time.time())
            response = requests.get(url, headers=self.headers)
            print(f"RESPONSE: {response.url}")
            self.__parse_time = time.time()
            if response.status_code == 200:
                return response

    def get_task(self, url: str, callback: typing.Callable) -> typing.Callable:
        def task():
            response = self._get_response(url)
            return callback(response)

        return task

    def run(self):
        while True:
            try:
                task = self.tasks.pop(0)
                task()
            except IndexError:
                break

    def task_creator(self, urls: set, callback):
        urls_set = urls - self.done_url
        for url in urls_set:
            self.tasks.append(self.get_task(url, callback))
            self.done_url.add(url)

    def parse_feed(self, response: requests.Response):
        soup = bs4.BeautifulSoup(response.text, "lxml")
        ul_pagination = soup.find("ul", attrs={"class": "gb__pagination"})
        self.task_creator(
            {
                urljoin(response.url, a_tag.attrs["href"])
                for a_tag in ul_pagination.find_all("a")
                if a_tag.attrs.get("href")
            },
            self.parse_feed,
        )
        post_wrapper = soup.find("div", attrs={"class": "post-items-wrapper"})
        self.task_creator(
            {
                urljoin(response.url, a_tag.attrs["href"])
                for a_tag in post_wrapper.find_all("a", attrs={"class": "post-item__title"})
                if a_tag.attrs.get("href")
            },
            self.parse_post,
        )

    def parse_post(self, response: requests.Response):
        soup = bs4.BeautifulSoup(response.text, "lxml")
        author_name_tag = soup.find("div", itemprop="author")
        data = {
            "post_data": {
                "title": soup.find("h1", attrs={"class": "blogpost-title"}).text,
                "url": response.url,
                "id": int(soup.find("comments").attrs.get("commentable-id")),
            },
            "author_data": {
                "url": urljoin(response.url, author_name_tag.parent.attrs.get("href")),
                "name": author_name_tag.text,
            },
            "tags_data": [
                {"name": tag.text, "url": urljoin(response.url, tag.attrs.get("href"))}
                for tag in soup.find_all("a", attrs={"class": "small"})
            ],
            "comments_data": self._get_comments(soup.find("comments").attrs.get("commentable-id")),
        }
        self._save(data)

    def _get_comments(self, post_id):
        api_path = f"/api/v2/comments?commentable_type=Post&commentable_id={post_id}&order=desc"
        response = self._get_response(urljoin(self.start_url, api_path))
        data = response.json()
        return data

    def _save(self, data):
        self.db.add_post(data)


if __name__ == "__main__":
    db_client = Database("sqlite:///gb_db.db") # создаем db_client и указываем относительный путь к бд
    parser = GbBlogParse("https://gb.ru/posts", db_client, 1.0)
    parser.run()
  #  print(1)