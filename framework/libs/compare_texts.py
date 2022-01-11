def sum_similarity(model, text1, text2):
    tokens1, tokens2 = model(text1), model(text2)
    return sum([max([t1.similarity(t2) for t1 in tokens1 if t1.text != t2.text]) for t2 in tokens2])


def compare_words(model_wrapper, text1, text2):
    return model_wrapper.run(sum_similarity, text1, text2)


def similarity(model, word1, word2):
    token1 = model(word1)
    token2 = model(word2)
    return token1.similarity(token2) if word1.strip() and word2.strip() and token1.vector_norm and token2.vector_norm\
        else 0
