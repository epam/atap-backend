import re
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer


MATH_SYMBOLS = '+-=*/%'


def clean_text(text, flag=True):
    text = text.replace('\n', ' ')
    expression = '[^a-zA-Z0-9 ]'
    if flag:
        expression = expression[:-1] + MATH_SYMBOLS + ']'
    reg = re.compile(expression)
    return reg.sub('', text)


def clean_html(raw_html, alphabet_flag=False, stop_word_flag=False, stem_flag=False):
    """Clear html code from html elements, optionally clear stop words and normalize words"""

    cleantext = re.sub(re.compile('<.*?>'), '', raw_html)
    cleantext = re.sub('[@#$&{}()">]', ' ', cleantext)
    if alphabet_flag:
        cleantext = re.sub('[^a-zA-Z]', ' ', cleantext)
        cleantext = cleantext.lower()

    cleantext = cleantext.split()
    if stop_word_flag and stem_flag:
        stop_words = set(stopwords.words('english'))
        stem = PorterStemmer()
        cleantext = [stem.stem(word) for word in cleantext if word not in stop_words]
        while '' in cleantext:
            cleantext.remove('')

    elif stop_word_flag:
        stop_words = set(stopwords.words('english'))
        cleantext = [word for word in cleantext if word not in stop_words]
        while '' in cleantext:
            cleantext.remove('')
    elif stem_flag:
        stem = PorterStemmer()
        cleantext = [stem.stem(word) for word in cleantext]
        while '' in cleantext:
            cleantext.remove('')
    cleantext = " ".join([i for i in cleantext if not i.isdigit()])
    return cleantext