from nltk.corpus import stopwords
from threading import Lock

lock = Lock()


class Stopwords:
    def __init__(self):
        self.stop_words = None

    def get(self):
        with lock:
            if self.stop_words is None:
                self.stop_words = set(stopwords.words('english'))
            return self.stop_words


cached_stopwords = Stopwords()
