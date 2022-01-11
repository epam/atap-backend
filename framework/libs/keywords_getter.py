from collections import OrderedDict
import numpy as np
from spacy.lang.en.stop_words import STOP_WORDS
import re
from framework.libs.stop_words import cached_stopwords
from framework.libs.stemmer import cached_stemmer
from gensim.summarization.keywords import keywords
import wrapt_timeout_decorator
from threading import Lock


lock = Lock()


def get_vocab(text):
    """Get all tokens"""

    vocab = OrderedDict()
    counter = 0
    for sentence in text:
        for word in sentence:
            if word not in vocab:
                vocab[word] = counter
                counter += 1
    return vocab


def sentence_segment(doc, candidate_pos, lower):
    """Store those words only in candidate_pos"""

    sentences = []
    for sent in doc.sents:
        selected_words = []
        for token in sent:
            if token.pos_ in candidate_pos and token.is_stop is False:
                if lower is True:
                    selected_words.append(token.text.lower())
                else:
                    selected_words.append(token.text)
        sentences.append(selected_words)
    return sentences


def get_token_pairs(size, sentences):
    """Build token_pairs from windows in sentences"""

    token_pairs = list()
    for sentence in sentences:
        for i, word in enumerate(sentence):
            for j in range(i + 1, i + size):
                if j >= len(sentence):
                    break
                if (word, sentence[j]) is not token_pairs:
                    token_pairs.append((word, sentence[j]))
    return token_pairs


def get_matrix(vocab, token_pairs):
    """Get normalized matrix"""

    # build matrix
    matrix = np.zeros((len(vocab), len(vocab)), dtype='float')
    for w1, w2 in token_pairs:
        matrix[vocab[w1]][vocab[w2]] = 1

    # symmetrize matrix
    matrix += (matrix.T - np.diag(matrix.diagonal()))

    # normalize matrix by column, this is ignore the 0 element in norm
    norm = np.sum(matrix, axis=0)
    return np.divide(matrix, norm, where=(norm != 0))


def clean_text(text, stemmer):
    # clean text
    text = re.sub('[^a-zA-Z]', ' ', text).lower().split()

    stop_words = set(cached_stopwords.get())

    # normalize words
    return " ".join([stemmer.stem(word) if stemmer is not None else word for word in text if word not in stop_words])


def analyze(model, text, stemmer, candidate_pos, stop_w, size=5, lower=False):
    """General function to analyze text"""
    # # set stop words
    for word in STOP_WORDS.union(set(stop_w)):
        model.vocab[word].is_stop = True

    text = clean_text(text, stemmer)
    # filter sentences, pare text by spaCy
    try:
        sentences = sentence_segment(model(text), candidate_pos, lower)
    except ValueError:
        return None

    # build vocabulary
    vocab = get_vocab(sentences)

    # get normalize matrix
    matrix = get_matrix(vocab, get_token_pairs(size, sentences))

    # initialization for weight
    pr = np.array([1] * len(vocab))

    # iteration
    prev_pr = 0
    # 10 - iteration steps
    for epoch in range(10):
        pr = (1 - 0.85) + 0.85 * np.dot(matrix, pr)  # damping coefficient, usually is .85
        if abs(prev_pr - sum(pr)) < 1e-5:  # convergence threshold
            break
        else:
            prev_pr = sum(pr)

    # get weight for each node
    node_w = dict()
    for word, index in vocab.items():
        node_w[word] = pr[index]
    return node_w


class KeywordsGetter:
    def __init__(self, text, stemming=True):
        self.text = text
        self.stemmer = cached_stemmer if stemming else None

    def update_keywords(self, result, need_scores):
        if need_scores and self.stemmer is not None:
            tmp = dict()
            for word, score in result:
                key = self.stemmer.stem(word)
                if key not in tmp:
                    tmp[key] = score
                else:
                    tmp[key] += score
            result = [(k, v) for k, v in tmp.items()]
        elif self.stemmer is not None:
            result = {self.stemmer.stem(word) for word in result}
        return result

    def get_keywords_using_gensim(self, need_scores=False, number=None):
        with lock:
            @wrapt_timeout_decorator.timeout(60, use_signals=False)
            def get_keywords():
                words = (keywords(self.text.lower(), split=not need_scores, scores=need_scores) if number is None
                         else keywords(self.text.lower(), split=not need_scores, scores=need_scores, words=number))
                res = set(sum(map(lambda x: x.split(' '), words), [])) if not need_scores else sum(
                    map(lambda x: [(t, x[1]) for t in x[0].split(' ')], words), [])
                res = self.update_keywords(res, need_scores)
                return res
            try:
                return get_keywords()
            except TimeoutError:
                print("!!!gensim is frozen!!!!")
                return []

    def get_keywords_using_spacy(self, model_wrapper, number=10, pos=('NOUN', 'PROPN', 'VERB')):
        """Get top list keywords"""

        node_weight = model_wrapper.run(
            analyze,
            text=self.text,
            stemmer=self.stemmer,
            candidate_pos=pos,
            size=5,
            lower=False,
            stop_w=[]
        )

        if node_weight is None:
            return []
        node_w = OrderedDict(sorted(node_weight.items(), key=lambda t: t[1], reverse=True))
        return list(node_w.keys())[:min(len(node_w), number)]
