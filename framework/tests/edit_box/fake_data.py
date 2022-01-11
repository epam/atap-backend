import secrets
import string
from random import randint, choice
from selenium.webdriver.common.keys import Keys


def generate_random_password():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(15))

def generate_random_word(length):
   return ''.join(choice(string.ascii_lowercase) for i in range(length))

def generate_random_number(length):
   return str(randint(0, 10 ** length))

def generate_random_color():
    color = lambda: randint(0, 255)
    return f'#{color():02X}{color():02X}{color():02X}'


# def fake_data():
    # return {
        # "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
        # "sed do eiusmod tempor incididunt ut labore "
        # "et dolore magna aliqua.": {"long", "password"},
        # generate_random_password(): {"correct"},
        # "123456789101112": {"number"},
        # "♐ ♑ ♒ ♓ ❅ ❆ ❇ ❈": {"contain", "illeg"},
        # "               ": {"empti", "select"},
        # "": {"password", "charact", "includ", "letter", "number"}
    # }

# def fake_data():
#     return {'text': "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
#         "sed do eiusmod tempor incididunt ut labore "
#         "et dolore magna aliqua.",
#         'password': generate_random_password(),
#         'number': generate_random_number(15),
#         'tel': str(randint(0, 8e9)),
#         'email': f"{generate_random_word(randint(0, 20))}@mail",
#         'color': generate_random_color(),
#         'url': f'http://{generate_random_word(10)}/{generate_random_word(4)}?id={generate_random_number(5)}'
#     }

def fake_data():
    return {'text': Keys.TAB,
        'password': Keys.TAB,
        'number': Keys.TAB,
        'tel': Keys.TAB,
        'email': Keys.TAB,
        'color': Keys.TAB,
        'url': Keys.TAB
    }



def fake_personal_data():
    return {
        'addit',
        'additional',
        'address',
        'area',
        'bday',
        'cc',
        'code',
        'countri',
        'csc',
        'currenc',
        'day',
        'email',
        'exp',
        'family',
        'given',
        'impp',
        'languag',
        'level',
        'line',
        'month',
        'name',
        'nation',
        'nicknam',
        'number',
        'organ',
        'password',
        'photo',
        'prefix',
        'sex',
        'street',
        'suffix',
        'tel',
        'titl',
        'transact',
        'two',
        'type',
        'url',
        'username',
        'year'
    }
