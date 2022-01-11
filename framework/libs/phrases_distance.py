def distance(model, words_1, words_2):
    return model.wmdistance(words_1, words_2)


def tokens(model, sentence: str):
    return model.word_tokenize(sentence)
