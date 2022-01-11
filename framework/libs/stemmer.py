from nltk.stem.porter import PorterStemmer
from threading import Lock

lock = Lock()


class Stemmer:
    def __init__(self):
        self.stemmer = None

    def stem(self, word):
        with lock:
            if self.stemmer is None:
                self.stemmer = PorterStemmer()
            return self.stemmer.stem(word)


cached_stemmer = Stemmer()
