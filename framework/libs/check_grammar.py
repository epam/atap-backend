import pkg_resources
from symspellpy import SymSpell, Verbosity


def check_grammar(words):
    sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    dictionary_path = pkg_resources.resource_filename("symspellpy", "frequency_dictionary_en_82_765.txt")
    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)

    bad_words = []
    for word in words:
        suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2, include_unknown=True)
        if any(suggestion._distance != 0 for suggestion in suggestions):
            bad_words.append(word)
    return bad_words
