from framework.libs.keywords_getter import KeywordsGetter


def do_get_keywords(model, text, keys):

    return set(list([str(e) for e in keys]) or set([str(w) for w in model(text) if len(w) > 1]))


def re_keywords(model_wrapper, text):
    """
    Search keywords in text
    """
    if isinstance(text, str):
        getter = KeywordsGetter(text)
        keys = set(getter.get_keywords_using_spacy(model_wrapper)).union(set(getter.get_keywords_using_gensim()))
        return model_wrapper.run(do_get_keywords, text, keys)
    else:
        return set()
