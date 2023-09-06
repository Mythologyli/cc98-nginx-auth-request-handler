import base64
import os
import random
import time
from urllib.parse import urlsplit


class Session:
    def __init__(self, url: str = None, source_dict: dict = None):
        if source_dict:
            self.session_id = source_dict["session_id"]
            self.state = source_dict["state"]
            self.url = source_dict["url"]
            self.created_time = source_dict["created_time"]
            self.user_id = source_dict["user_id"]
            self.user_name = source_dict["user_name"]
        elif url:
            self.session_id = base64.urlsafe_b64encode(os.urandom(32)).decode()
            self.state = random.randint(0, 2 ** 32 - 1)
            self.url = url
            self.created_time = int(time.time())
            self.user_id = -1
            self.user_name = ""
        else:
            raise ValueError("URL and source_dict cannot be both None")

    def base_url(self) -> str:
        return "{0.scheme}://{0.netloc}".format(urlsplit(self.url))

    def is_expired(self, expires: int) -> bool:
        return int(time.time()) > self.created_time + expires

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "state": self.state,
            "url": self.url,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "created_time": self.created_time,
        }
