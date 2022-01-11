from selenium import webdriver
from PIL import Image
import cv2 as cv
import numpy as np
import tempfile
from collections import OrderedDict, Counter, defaultdict
import operator

from framework.activity import Activity
from framework.element_locator import ElementLocator
from framework.screenshot.screenshot import Screenshot
from framework.libs.hide_cookie_popup import hide_cookie_popup


name = '''Ensures that contrast ratio for adjacent elements doesn't violate requirements'''
WCAG = '1.4.11'
framework_version = 0
webdriver_restart_required = False

elements_type = ""
test_data = [
    {
        "page_info": {
            "url": "scaling/page_bugs_scaling.html"
        },
        "expected_status": "PASS"
    },
    {
        "page_info": {
            "url": "page_bad_contrast.html"
        },
        "expected_status": "FAIL"
    }
]


def test(webdriver_instance: webdriver.Firefox, activity: Activity, element_locator: ElementLocator):
    """
    Tests a web page for WCAG 2.1 1.4.11 criterion.
    Detects contrast ratio violations by adjacent groups of pixels.
    Gives 'PASS' and 'ERROR' status.
    Parameters of the function satisfy the framework requirements.
        More details on: http://confluence:8090/display/RND/Accessibility+Testing+Framework
    Returns test result as a dict:
    result = {
                'status': <'ERROR', 'PASS' or 'NOTRUN'>,
                'message': <string>,
                'elements': [],
                'checked_elements': []
             }
    """
    result = {'status': 'PASS',
              'message': '',
              'checked_elements': []
              }
    # take a screenshot of a page

    activity.get(webdriver_instance)
    hide_cookie_popup(webdriver_instance, activity)
    screenshot = Screenshot.full_page(webdriver_instance)
    file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    screenshot.save(file.name)

    add_contours(file.name, file.name)
    resize_image(file.name, 0.5)
    problems = create_groups_of_pixels(file.name)
    file.close()

    # locate problems on the page and take screenshot
    # problems = error_fragmentation(src_pic, problems)
    if problems:
        result['status'] = 'FAIL'
        result['message'] = 'Found {} fragments with unsatisfying contrast rate.'.format(len(problems))

    return result


def error_fragmentation(src_pic, problem_areas):
    """
    Draws a red rectangle on the screenshot around area, where contrast ratio was violated.
    src_pic = screenshot to draw on
    problem_areas = (ratio, area):
        ratio = numeric value of ratio
        area = [highest, lowest, leftest, rightest] = list of rectangle coordinates - two points
    """
    problem_files = dict()
    for colors, areas in problem_areas.items():
        file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        image = cv.cvtColor(np.array(cv.imread(src_pic)), cv.COLOR_RGB2BGR)
        cv.imwrite(file.name, image)

        for area in areas:
            image = cv.cvtColor(np.array(cv.imread(file.name)), cv.COLOR_RGB2BGR)
            try:
                # highest, lowest, leftest, rightest
                (x, y, x1, y1) = area[2], area[0], area[3], area[1]
                cv.rectangle(image, (x, y), (x1, y1), (0, 0, 255), 1)
            except TypeError:
                print("Exception happened during building borders for this area: {} stands for (y, y1, x, x1)".format(area))
                height, width, channels = image.shape
                print("Image sizes are: {0} - height, {1} - width".format(height, width))
                return False
            cv.imwrite(file.name, image)
        problem_files[colors] = file.name
    return problem_files


def add_contours(src_pic, output_src):
    """
    Draws contours on a screenshot of a page to minimize the impact of browser pixel smoothing.
    Uses OpenCV functions: findContours and drawContours.
    Saves src_pic with contours in output_src.
    """
    # Load the image and convert it to grayscale
    image = cv.imread(src_pic)
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

    # Add some extra padding around the image
    # gray = cv.copyMakeBorder(gray, 8, 8, 8, 8, cv.BORDER_REPLICATE)

    # threshold the image (convert it to pure black and white)
    thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU)[1]

    # find the contours (continuous blobs of pixels) the image
    contours = cv.findContours(thresh.copy(), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    contours = contours[0]

    # final = np.zeros(image.shape, np.uint8)
    # mask = np.zeros(gray.shape, np.uint8)

    # print(contours[0][0])
    # print(type(contours[0][1]))
    # print(len(contours), '   ----------------- length')

    lst_intensities = []

    for i in range(len(contours)):
        cimg = np.zeros_like(image)
        cv.drawContours(cimg, contours, i, color=255, thickness=-1)
        # Access the image pixels and create a 1D numpy array then add to list
        pts = np.where(cimg == 255)
        lst_intensities.append(image[pts[0], pts[1]])
        color_freq_dict = Counter(map(lambda x: (int(x[2]), int(x[1]), int(x[0])), lst_intensities[i]))
        color = max(OrderedDict(sorted(color_freq_dict.items())).items(), key=operator.itemgetter(1))[0]
        cv.drawContours(image, contours, i, color, 3)

    cv.imwrite(output_src, image)


def resize_image(path, scale):
    img = Image.open(path)
    img.thumbnail(tuple(map(lambda x: x * scale, img.size)), Image.ANTIALIAS)
    img.save(path)


def create_groups_of_pixels(src_pic):
    """
    Processes an image for finding contrast ratio violations.
    Divides an image into groups of adjacent pixels of the one colour, checks ratio of each group with its neighbours
    (adjacent groups).
    Returns a list of pairs:
        problems = (ratio, area):
            ratio = numeric value of ratio
            area = [highest, lowest, leftest, rightest] = list of rectangle coordinates - two points
    """

    # get screenshot
    image = Image.open(src_pic)
    # convert rgba to rgb
    image = image.convert('RGB')

    # get pixel colors
    # get rgb values of pixels in screenshot

    pix_values = list(image.getdata())
    pixels = [[] for y in range(image.size[1])]
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            try:
                pixels[y].append(pix_values[y * image.size[0] + x])
            except IndexError:
                print('y: ', y)
                print('x: ', x)
                print('length pix_values: ', len(pix_values))
                print('image 0: ', image.size[0])
                print('image 1: ', image.size[1])
                break

    # create groups of pixels by color
    groups = {}
    # group number for each pixel
    pix_groups = {}
    # list of pairs of groups which are neighbours
    neighbours = []
    # count of groups
    groups_cnt = 0
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            # the first line; check without going higher
            if y == 0:
                if x == 0:
                    # print('new group created {}'.format(pixels[y][x]))
                    pix_groups[(y, x)] = groups_cnt
                    groups_cnt += 1
                    groups[pix_groups[(y, x)]] = [(y, x)]
                else:
                    if pixels[y][x-1] == pixels[y][x]:
                        pix_groups[(y, x)] = pix_groups[(y, x - 1)]
                        groups[pix_groups[(y, x - 1)]].append((y, x))
                    else:
                        # print('new group created {}'.format(pixels[y][x]))
                        pix_groups[(y, x)] = groups_cnt
                        groups_cnt += 1
                        groups[pix_groups[(y, x)]] = [(y, x)]
                        if {pix_groups[(y, x-1)], pix_groups[(y, x)]} not in neighbours:
                            neighbours.append({pix_groups[(y, x-1)], pix_groups[(y, x)]})

            # the first column; check without going left
            elif x == 0:
                if pixels[y-1][x] == pixels[y][x]:
                    pix_groups[(y, x)] = pix_groups[(y - 1, x)]
                    groups[pix_groups[(y - 1, x)]].append((y, x))
                else:
                    # print('new group created {}'.format(pixels[y][x]))
                    pix_groups[(y, x)] = groups_cnt
                    groups_cnt += 1
                    groups[pix_groups[(y, x)]] = [(y, x)]
                    if {pix_groups[(y-1, x)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y-1, x)], pix_groups[(y, x)]})

            # other pixels
            else:
                if pixels[y-1][x] == pixels[y][x]:
                    pix_groups[(y, x)] = pix_groups[(y-1, x)]
                    groups[pix_groups[(y-1, x)]].append((y, x))
                elif pixels[y][x-1] == pixels[y][x]:
                    pix_groups[(y, x)] = pix_groups[(y, x-1)]
                    groups[pix_groups[(y, x-1)]].append((y, x))
                    if {pix_groups[(y-1, x)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y-1, x)], pix_groups[(y, x)]})
                elif pixels[y-1][x-1] == pixels[y][x]:
                    pix_groups[(y, x)] = pix_groups[(y-1, x-1)]
                    groups[pix_groups[(y-1, x-1)]].append((y, x))
                    if {pix_groups[(y-1, x)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y-1, x)], pix_groups[(y, x)]})
                    if {pix_groups[(y, x-1)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y, x-1)], pix_groups[(y, x)]})
                else:
                    # print('new group created {}'.format(pixels[y][x]))
                    pix_groups[(y, x)] = groups_cnt
                    groups_cnt += 1
                    groups[pix_groups[(y, x)]] = [(y, x)]
                    if {pix_groups[(y-1, x)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y-1, x)], pix_groups[(y, x)]})
                    if {pix_groups[(y, x-1)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y, x-1)], pix_groups[(y, x)]})
                    if {pix_groups[(y-1, x-1)], pix_groups[(y, x)]} not in neighbours:
                        neighbours.append({pix_groups[(y-1, x-1)], pix_groups[(y, x)]})

    ignore_groups = []
    groups_representatives = {}
    for key, value in groups.items():
        highest = image.size[1]
        lowest = 0
        leftest = image.size[0]
        rightest = 0
        for pixel in value:
            if pixel[0] < highest:
                highest = pixel[0]
            if pixel[0] > lowest:
                lowest = pixel[0]
            if pixel[1] > rightest:
                rightest = pixel[1]
            if pixel[1] < leftest:
                leftest = pixel[1]
        if abs(highest - lowest) < 4 or abs(rightest - leftest) < 4:
            ignore_groups.append(key)
        groups_representatives[key] = [highest, lowest, leftest, rightest]

    problem_areas = defaultdict(set)
    for pair in neighbours:
        # pair = (id1, id2)
        id1 = pair.pop()
        id2 = pair.pop()
        if id1 not in ignore_groups and id2 not in ignore_groups:
            color_1 = pixels[groups[id1][0][0]][groups[id1][0][1]]
            color_2 = pixels[groups[id2][0][0]][groups[id2][0][1]]
            color_1_2 = relative_luminance(color_1)
            color_2_2 = relative_luminance(color_2)
            ratio = max((color_1_2 + 0.05) / (color_2_2 + 0.05), (color_2_2 + 0.05) / (color_1_2 + 0.05))
            if ratio < 3:
                # problem_groups.append(ratio)
                group_represents1 = groups_representatives[id1]
                group_represents2 = groups_representatives[id2]
                problem_areas[tuple(sorted([color_1, color_2]))].add(
                    (min(group_represents1[0], group_represents2[0]), max(group_represents1[1], group_represents2[1]),
                     min(group_represents1[2], group_represents2[2]), max(group_represents1[3], group_represents2[3])))

    return problem_areas


def relative_luminance(rgb):
    """
    Calculates relative luminance for a color in RGB scale.
    """
    odds = [0.2126, 0.7152, 0.0722]  # sensitivity of the human eye to individual components of light (R,G,B)
    return sum(n1 * n2 for n1, n2 in zip(odds, map(_linear_value, rgb)))


def _linear_value(color):
    if color <= 0.03928:
        return color / 12.92
    return ((color + 0.055) / 1.055) ** 2.4
