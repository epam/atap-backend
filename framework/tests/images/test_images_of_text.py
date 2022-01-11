from tempfile import NamedTemporaryFile
import numpy as np
from PIL import Image
import cv2
from skimage.filters import threshold_yen, threshold_sauvola
from skimage.exposure import rescale_intensity
from scipy.signal import find_peaks

from easyocr import Reader

from selenium import webdriver

from framework.libs.download_image import get_image_element, wont_read_or_rgba
from framework.element_locator import ElementLocator

depends = []
name = "Ensures that image from web document does not contain text"
WCAG = "1.4.5"
locator_required_elements = ["img"]
framework_version = 5
webdriver_restart_required = False
elements_type = "image"

test_data = [
    {
        "page_info": {"url": "images/images_of_text/page_bug_image_with_text.html"},
        "expected_status": "WARN",
        "expected_additional_content_length": {"elements": 26},
    },  # 2 FN: day start, coca-cola; 1 FP player
    {
        "page_info": {"url": "images/images_of_text/page_good_image_with_text.html"},
        "expected_status": "PASS",
    },
    {
        "page_info": {"url": "images/images_of_text/page_no_elements.html"},
        "expected_status": "NOELEMENTS",
    },
    {
        "page_info": {"url": "images/images_of_text/page_kylie_jean.html"},
        "expected_status": "WARN",
        "expected_additional_content_length": {"elements": 15},
    },  # 1 FN: double ny
]


def set_image_dpi(file_path, img_size, dpi=300):
    temp_file = NamedTemporaryFile(delete=False, suffix=".png")
    temp_filename = temp_file.name

    im = Image.open(file_path)
    length_x, width_y = im.size
    factor = img_size / length_x
    size = int(factor * length_x), int(factor * width_y)

    im_resized = im.resize(size, Image.ANTIALIAS)
    im_resized.save(temp_filename, dpi=(dpi, dpi))

    return temp_file


def status_result(checked, failed):
    result = {
        "status": "PASS",
        "message": "All img elements do not contain text.",
        "elements": [],
        "checked_elements": checked,
    }

    if failed:
        result["status"] = "WARN"
        result["message"] = "Images with text are to be replaced with CSS."
        result["elements"] = [
            {"element": img, "problem": "Text is prohibited", "severity": "FAIL", "error_id": "ImageOfText"}
            for img in failed
        ]

    return result


def collect_images_of_text(checked_images, driver, save_text=False, large_image=False):
    text_images = []
    text_data = []

    for image in checked_images:
        image_file = get_image_element(driver, image)

        if wont_read_or_rgba(image_file):
            print("force_screenshot")
            image_file = get_image_element(driver, image, force_screenshot=True)

        image_src = image.safe_operation_wrapper(
            lambda elem: elem.get_attribute(driver, "src"), lambda lost: print("LOST SRC")
        )
        print("\nimage src", image_src)

        image_feature_wrapper = TextFeaturePreprocessor(image_file.name, image_src, large_image=large_image)
        image_feature_wrapper.detect_text()

        # * text finally found
        if image_feature_wrapper.image_of_text:
            text_images.append(image)
            if save_text:
                text_data.append(image_feature_wrapper.text_data)

        print("*****************")
        print("text_data", image_feature_wrapper.text_data)
        print("image_of_text", image_feature_wrapper.image_of_text)
        print("*****************")

    return text_images, text_data


def test(webdriver_instance: webdriver.Firefox, activity, element_locator: ElementLocator):
    activity.get(webdriver_instance)
    images = element_locator.get_all_of_type(webdriver_instance, element_types=locator_required_elements)
    webdriver_instance.execute_script("window.scrollTo(0, 0);")
    top_images = [*filter(lambda elem: elem.is_displayed(webdriver_instance), images)]
    webdriver_instance.execute_script("window.scrollTo(document.body.scrollWidth, document.body.scrollHeight);")
    bottom_images = [*filter(lambda elem: elem.is_displayed(webdriver_instance), images)]
    images, top_images, bottom_images = [*set([*top_images, *bottom_images])], None, None

    print("\nlocated images", len(images))
    print("located images", images)

    if not images:
        return {
            "status": "NOELEMENTS",
            "message": "There are no images for testing.",
            "elements": [],
            "checked_elements": [],
        }

    images_of_text, _ = collect_images_of_text(images, webdriver_instance)

    result = status_result(images, images_of_text)

    print("***********************************************RESULT***********************************************")
    print(result)
    return result


class TextFeaturePreprocessor:

    # * guessed params for pattern_image
    IMAGE_SIZE = 1000
    CUTOUT_SECTOR = 200

    def __init__(self, file, src, large_image=False):
        self.large_image = large_image
        self.IMAGE_SIZE = 2200 if large_image else self.IMAGE_SIZE
        self.image_file = set_image_dpi(file, self.IMAGE_SIZE)
        self.image = cv2.imread(self.image_file.name, cv2.IMREAD_UNCHANGED)
        self.enhanced_image = None
        self.binary_image = None
        self.pattern_image = None
        self.src = src  # auxillary
        self.temp_files = {code: NamedTemporaryFile(delete=False, suffix=".png") for code in ("enh", "bin", "pat")}
        self.probability_threshold = 0.15 if self.large_image else 0.085  # * will cutout recognized
        self.text_data = []
        self.image_of_text = False

    def make_square(self, image, fill_color=(255, 255, 255)):
        image = Image.fromarray(image)
        x, y = image.size
        size = max(self.IMAGE_SIZE, x, y)

        if size > self.IMAGE_SIZE:
            new_image = image
            new_image.thumbnail((self.IMAGE_SIZE, self.IMAGE_SIZE))
        else:
            new_image = Image.new("RGB", (size, size), fill_color)
            new_image.paste(image, (int((size - x) / 2), int((size - y) / 2)))

        return np.asarray(new_image)

    def enhance_grayscale(self):
        image = self.image
        if len(image.shape) == 3:
            cvt_color = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
            gray = cv2.cvtColor(image, cvt_color)
        else:
            gray = image

        yen_threshold = threshold_yen(gray)
        image = rescale_intensity(gray, (0, yen_threshold * 2), (0, 255)).astype(np.uint8)

        alpha = 0.7  # contrast
        beta = 80  # brightness
        image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

        image = image + gray

        clahe = cv2.createCLAHE(clipLimit=5)  # 5, 60
        image = clahe.apply(image)
        image = cv2.equalizeHist(image)

        self.enhanced_image = image

    def adapt_threshhold(self):
        image = self.enhanced_image

        window_size = 3
        thresh_sauvola = threshold_sauvola(image, window_size=window_size, k=1)
        sci_bw = 255 - thresh_sauvola

        thresh, im_bw_low = cv2.threshold(cv2.bitwise_not(image), 65, 255, cv2.THRESH_TRUNC + cv2.THRESH_OTSU)
        thresh, im_bw_med = cv2.threshold(image, 150, 255, cv2.THRESH_TRUNC + cv2.THRESH_OTSU)
        thresh, im_bw_high = cv2.threshold(image, 230, 255, cv2.THRESH_TRUNC + cv2.THRESH_OTSU)

        blacky = [*map(lambda im_bw: np.sum(im_bw == 0), [im_bw_low, im_bw_med, im_bw_high])]
        im_bw = [im_bw_low, im_bw_med, im_bw_high][blacky.index(max(blacky))]

        im_bw = im_bw - sci_bw
        im_bw = (im_bw - np.min(im_bw)) / (np.max(im_bw) - np.min(im_bw)) * 255
        hist, bin_edges = np.histogram(im_bw, bins=280)
        bin_edges = bin_edges[1:]
        peaks, _ = find_peaks(hist, distance=5, threshold=5, height=1000)
        peaks = [*map(lambda p: round(255 / 280 * p), peaks)]

        dy = np.abs(np.diff(np.diff(peaks)))
        if len(dy) >= 2:
            peak_min = peaks[::-1][[*dy][::-1].index(np.min(dy))]
            peak_max = peaks[[*dy].index(np.max(dy)) + 2]
        else:
            peak_max = 230
            peak_min = 120

        peak_max = abs(peak_min - peak_max) >= 10 and peak_max or peak_max + 20

        _ = np.where(im_bw < peak_min, 255, 0).astype(dtype=np.uint8)
        _ = cv2.bitwise_or(np.where(im_bw < peak_max, 255, 0).astype(dtype=np.uint8), _)
        _ = cv2.bitwise_xor(np.where(im_bw < 230, 255, 0).astype(dtype=np.uint8), _)

        # false threshold
        if np.unique(_).__len__() != 2:
            peak_max = 230
            peak_min = 120
            _ = np.where(im_bw < peak_min, 255, 0).astype(dtype=np.uint8)
            _ = cv2.bitwise_xor(np.where(im_bw < peak_max, 255, 0).astype(dtype=np.uint8), _)
        im_bw = _

        thresh, im_bw = cv2.threshold(im_bw, 130, 255, cv2.THRESH_BINARY)

        assert np.sum(np.unique(im_bw)) == 255
        im_bw = im_bw if np.sum(im_bw == 0) < np.sum(im_bw == 255) else cv2.bitwise_not(im_bw)

        self.binary_image = im_bw

    def noise_removal(self):
        image = self.binary_image
        kernel = np.ones((1, 1), np.uint8)
        image = cv2.dilate(image, kernel, iterations=6)
        image = cv2.erode(image, kernel, iterations=4)

        opening = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        image = cv2.bitwise_and(image, closing)

        self.binary_image = image

    def erode_font(self):
        image = cv2.bitwise_not(self.binary_image)

        kernel = np.ones((2, 1), np.uint8)
        image = cv2.dilate(image, kernel, iterations=2)
        image = cv2.blur(image, (1, 3))
        image = cv2.erode(image, kernel, iterations=2)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 2))
        image = cv2.morphologyEx(image, cv2.MORPH_HITMISS, kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 3))
        image = cv2.morphologyEx(image, cv2.MORPH_GRADIENT, kernel, iterations=2)

        image = cv2.bitwise_not(image)

        self.pattern_image = image

    def cover_scene(self):
        font, amn, _ = self.remove_text_scene(self.image.copy(), self.pattern_image.copy())
        times = (amn <= 7 and 1) or (amn > 7 and amn <= 32 and 2) or (amn > 32 and amn <= 40 and 3) or 4
        self.pattern_image = self.timestych_rebuild(self.image.copy(), self.pattern_image.copy(), times=times)

    # TODO simplify me
    def remove_text_scene(self, scene_image, scene_bw, nasty_font=False, last_amount=0):
        if len(scene_image.shape) == 3:
            cvt_color = cv2.COLOR_BGRA2GRAY if scene_image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
            gray_image = cv2.cvtColor(scene_image, cvt_color)
        else:
            gray_image = scene_image

        blur = cv2.blur(gray_image, (11, 11))
        blur = cv2.medianBlur(blur, 5)
        blur = cv2.bilateralFilter(blur, 3, 20, 20)

        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        thresh = cv2.bitwise_and(thresh, scene_bw) if nasty_font else thresh

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 7))
        dilate_mask = np.ones(thresh.shape, np.uint8) * 255
        dilate = cv2.dilate(thresh, kernel, iterations=2)

        dilate = (
            cv2.bitwise_and(dilate, thresh, mask=dilate_mask)
            if not nasty_font
            else cv2.bitwise_xor(dilate, thresh, mask=dilate_mask)
        )

        contours, hierarchy = cv2.findContours(dilate, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        cnt_sizes = [cv2.contourArea(cnt) for cnt in contours]
        cnt_rects = [cv2.boundingRect(cnt) for cnt in contours]
        rect_dims = [dims[2] * dims[3] for dims in cnt_rects]

        try:
            max_dims = max(rect_dims)
        except ValueError:
            # print("CONTOURS FAIL")
            return False, last_amount, scene_bw

        mean_size = min(int(np.mean(cnt_sizes)) or 1, max_dims)
        amount = len(contours)

        if not last_amount or nasty_font and amount != last_amount:
            nasty_font = not nasty_font or amount > last_amount and not last_amount < 3
            return self.remove_text_scene(scene_image, scene_bw, nasty_font=nasty_font, last_amount=amount)

        def will_take_contour(sizes, dimensions):
            upper_limit = max_dims if amount < 5 else (mean_size + max_dims) // 2

            return sizes > scene_image.shape[0] // 2 and dimensions < upper_limit + 10

        contours = [
            cnt for cnt, size, dims in zip(contours, cnt_sizes, rect_dims) if will_take_contour(size, dims)
        ]
        cnt_rects = [cv2.boundingRect(cnt) for cnt in contours]

        amount = len(contours)

        text_mask = np.zeros(scene_bw.shape, np.uint8) if nasty_font else dilate_mask
        cropped = text_mask
        area_val = 255 if nasty_font else 0

        for cnt, rect in zip(contours, cnt_rects):
            x, y, w, h = rect
            cv2.rectangle(scene_image, (x, y), (x + w, y + h), (36, 255, 12), 2)
            cv2.drawContours(text_mask, [cnt], -1, (area_val,) * 3, -1)

        cropped[text_mask == area_val] = scene_bw[text_mask == area_val]
        (y, x) = np.where(text_mask == area_val)
        if not len(x) + len(y):
            cropped_bw = np.zeros(scene_bw.shape, np.uint8)
        else:
            cropped_bw = cropped[:, :]

        return nasty_font, amount, cropped_bw

    # TODO simplify me
    def timestych_rebuild(self, image, image_bw, times):
        width, height = image.shape[:-1]

        def make_piece(img, primary=1, normal=1):
            return [
                img[
                    height * p // primary : height * (p + 1) // primary,
                    width * n // normal : width * (n + 1) // normal,
                ]
                for p in range(primary)
                for n in range(normal)
            ]

        pieces, pieces_bw = make_piece(image, times, times), make_piece(image_bw, times, times)
        straps, bands = make_piece(image, normal=times), make_piece(image, primary=times)
        straps_bw, bands_bw = make_piece(image_bw, normal=times), make_piece(image_bw, primary=times)

        for m in range(times):
            _, _, bands[m] = self.remove_text_scene(bands[m], bands_bw[m])
            _, _, straps[m] = self.remove_text_scene(straps[m], straps_bw[m])

            cropped = image_bw[height * m // times : height * (m + 1) // times, :]
            image_bw[height * m // times : height * (m + 1) // times, :] = cv2.bitwise_and(cropped, bands[m])
            cropped = image_bw[:, width * m // times : width * (m + 1) // times]
            image_bw[:, width * m // times : width * (m + 1) // times] = cv2.bitwise_and(cropped, straps[m])

        for m in range(times):
            for n in range(times):
                i = m * times + n
                x1, x2, y1, y2 = width * n, width * (n + 1), height * m, height * (m + 1)
                x1, x2, y1, y2 = [c // times for c in (x1, x2, y1, y2)]

                _, _, pieces[i] = self.remove_text_scene(pieces[i], pieces_bw[i])

                pieces[i] = (
                    cv2.bitwise_not(pieces[i])
                    if (np.sum(pieces[i] == 0) > np.sum(pieces[i] < 300) // 2) and (np.sum(pieces[i] > 0) > 0)
                    else pieces[i]
                )
                image_bw[y1:y2, x1:x2] = pieces[i]

        return image_bw

    def fragments_removal(self):
        image = self.pattern_image
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 50))
        h_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, v_kernel)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 4))
        v_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, h_kernel)
        _ = cv2.add(h_morph, v_morph)

        ell_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
        f_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, ell_kernel)
        _ = cv2.add(_, f_morph)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 11))
        f_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, rect_kernel)
        _ = cv2.add(_, f_morph)
        cross_kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (18, 15))
        f_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, cross_kernel)
        _ = cv2.add(_, f_morph)

        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 200))
        h_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, v_kernel)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (200, 1))
        v_morph = 255 - cv2.morphologyEx(image, cv2.MORPH_CLOSE, h_kernel)
        _ = cv2.add(_, h_morph)
        _ = cv2.add(_, v_morph)

        self.pattern_image = cv2.add(_, image)

    def cutout_localized(self):
        bg_image = self.pattern_image
        accurate_image = self.enhanced_image.copy()
        blank_mask = np.zeros((self.CUTOUT_SECTOR, self.CUTOUT_SECTOR), np.uint8)

        start_x, end_x = 0, self.CUTOUT_SECTOR
        while start_x < bg_image.shape[0]:
            start_y, end_y = 0, self.CUTOUT_SECTOR
            while start_y < bg_image.shape[1]:

                _ = bg_image[start_x:end_x, start_y:end_y]
                if len(np.unique(_)) == 1:
                    accurate_image[start_x:end_x, start_y:end_y] = cv2.bitwise_and(_, _, mask=blank_mask)
                start_y, end_y = [*map(lambda size: size + self.CUTOUT_SECTOR, (start_y, end_y))]
            start_x, end_x = [*map(lambda size: size + self.CUTOUT_SECTOR, (start_x, end_x))]

        self.pattern_image = accurate_image

    def mosaic_enhanced(self):
        self.pattern_image = cv2.bitwise_and(self.binary_image, self.binary_image, mask=self.pattern_image)

        self.pattern_image = cv2.bilateralFilter(self.pattern_image, 4, 40, 25)
        self.fragments_removal()  # last image =
        self.pattern_image = cv2.medianBlur(self.pattern_image, 3)  # (3, 3), 21, 9

        ell_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))  # 7 7
        self.pattern_image = cv2.morphologyEx(self.pattern_image, cv2.MORPH_DILATE, ell_kernel, iterations=2)
        ell_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))  # 7 7
        self.pattern_image = cv2.morphologyEx(self.pattern_image, cv2.MORPH_ERODE, ell_kernel, iterations=2)

        self.pattern_image = cv2.blur(self.pattern_image, (1, 3))
        self.pattern_image = cv2.medianBlur(self.pattern_image, 1)

        self.cutout_localized()

    def write_filtered_images(self):
        _ = [
            *map(
                lambda code, image: image is not None and cv2.imwrite(self.temp_files.get(code).name, image),
                ["enh", "bin", "pat"],
                [self.enhanced_image, self.binary_image, self.pattern_image],
            )
        ]

    @staticmethod
    def detected_square(bbox_arr):
        square = 0

        for bbox in bbox_arr:
            top_left, top_right, bottom_right, bottom_left = bbox
            width, height = top_right[0] - top_left[0], bottom_left[1] - top_left[1]
            square += int(width) * int(height)

        return square

    def best_magnification_data(self, magnification_set, recognizer, square_tol=1.2):
        best_mag_ratio, best_recognized = magnification_set[0], []

        def nth_of_nested(collection, n):
            return [*zip(*collection)][n]

        for mag_ratio in magnification_set:
            recognized = recognizer(mag_ratio)

            if not recognized:
                continue
            # need to init best_recognized
            if mag_ratio == magnification_set[0]:
                pass
            # * probability decreased, detected amount did not increase much
            elif round(sum(nth_of_nested(recognized, 2)), 3) <= round(
                sum(nth_of_nested(best_recognized, 2), 3)
            ) and square_tol * self.detected_square(nth_of_nested(best_recognized, 0)) > self.detected_square(
                nth_of_nested(recognized, 0)
            ):
                if sum(nth_of_nested(best_recognized, 2)) < 0.7:
                    print("best < 0.7: continue")
                    continue
                break

            best_mag_ratio = mag_ratio
            best_recognized = recognized

            print("\nrecognized", recognized)
            print("\nproba sum", sum(nth_of_nested(recognized, 2)))
            print("\nproba sum best", sum(nth_of_nested(best_recognized, 2)))

        return best_mag_ratio, best_recognized

    def recognized_data(self, reader, namecode, settings):
        filename = (self.temp_files.get(namecode) or self.image_file).name
        self.best_mag_ratio = self.best_mag_ratio or settings.get("mag_ratio")

        def handle_recognized(mag_ratio, wordlen=4):
            """
            * for the first time will download model
            * drop less than 4 characther for text values, except for high prob: "home"
            * drop with small probability
            """
            nonlocal filename
            nonlocal settings

            settings["mag_ratio"] = mag_ratio
            confidence_prob = 0.1 if self.large_image else 0.23

            return [
                *filter(
                    lambda data: len(data[0]) > wordlen
                    and data[2] > self.probability_threshold
                    or data[2] > confidence_prob,
                    reader.readtext(
                        filename,
                        **settings,
                    ),
                )
            ]

        try:
            mag_ratio, recognized = self.best_magnification_data(self.best_mag_ratio, handle_recognized)
        except RuntimeError:
            self.recognize_text(gpu=False)

        self.best_mag_ratio = [mag_ratio]

        return recognized

    # * main for 'recognize'
    def recognize_text(self, **kwargs):
        config = dict(
            lang_list=["en"],
            gpu=True,
            recog_network="standard",
            user_network_directory=None,
            model_storage_directory="/models/easy_ocr",  # !cannot unzip model
            detector=True,
            recognizer=True,
            download_enabled=True,
        )
        for kw, val in kwargs.items():
            config[kw] = val

        reader = Reader(**config)

        recognition_settings = dict(
            decoder="wordbeamsearch",
            beamWidth=3,
            paragraph=False,
            rotation_info=[90, 270],
            min_size=45,
            contrast_ths=0.6,
            adjust_contrast=0.25,
            text_threshold=0.9,
            low_text=0.35,
            link_threshold=0.6,
            mag_ratio=[1.1],
            slope_ths=0.2,
            ycenter_ths=0.5,
            height_ths=1,
            width_ths=1,
            add_margin=0.1,
        )

        if not self.large_image:
            return self.assured_text_data(reader, recognition_settings)

        for setting, value in zip(
            [
                "rotation_info",
                "text_threshold",
                "low_text",
                "mag_ratio",
                "slope_ths",
                "ycenter_ths",
                "height_ths",
                "width_ths",
            ],
            [[45, 90, 135, 270], 0.7, 0.25, [1, 0.85, 0.72, 0.5, 0.2], 0.1, 0, 0.5, 0.5],
        ):
            recognition_settings[setting] = value

        return self.accurate_text_data(reader, recognition_settings)

    def accurate_text_data(self, reader, settings):
        text = self.main_text_decorator(
            reader, None, settings, "original text"
        )

        # * changed self.best_mag_ratio in best_magnification_data cycle
        print("\n***********************************************")
        print("set best_mag_ratio", self.best_mag_ratio[0])
        _ = self.recognized_data(reader, "enh", settings)
        text.extend(_)
        print("***********************************************")
        print("enhanced text", _)
        if not len(_):
            _ = self.recognized_data(reader, "bin", settings)
            text.extend(_)
            print("***********************************************")
            print("binary text", _)

        return text

    def assured_text_data(self, reader, settings):
        text = self.main_text_decorator(
            reader, "pat", settings, "pattern text"
        )

        # * changed self.best_mag_ratio in best_magnification_data cycle

        # * pattern image recognition data is poor enough to validate another variants
        alternatives = iter(("enh", "bin", None))
        for alt in alternatives:
            if len(text) <= 1:
                _ = self.recognized_data(reader, alt, settings)
                text.extend(_)
                print("***********************************************")
                print("alternative text", _)

        return text

    def main_text_decorator(self, reader, filename, settings, text_name):
        self.best_mag_ratio = None
        result = self.recognized_data(reader, filename, settings)
        print('***********************************************')
        print(text_name, result)
        return result

    def draw_result(self, recognized):
        for (bbox, text, prob) in recognized:
            top_left, top_right, bottom_right, bottom_left = bbox
            top_left = (int(top_left[0]), int(top_left[1]))
            bottom_right = (int(bottom_right[0]), int(bottom_right[1]))

            # * show recognized result
            # create a rectangle for bbox display
            cv2.rectangle(img=self.image, pt1=top_left, pt2=bottom_right, color=(0, 0, 255), thickness=3)
            # put recognized text
            cv2.putText(
                img=self.image,
                text=text,
                org=(top_left[0], top_left[1] - 10),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(36, 255, 12),
                thickness=3,
            )
            # try:
            #     cv2.imwrite(f'reports/images/{self.src.split("/")[-1]}', self.image)
            # except:
            #     print(f'CANNOT IMWRITE {self.src.split("/")[-1]}')

    def drop_incidental(self, ocr_data, safe_amount=8):
        # * guess
        q_val = 0.2 + 0.009 * len(ocr_data)
        cutout_prob = np.quantile(np.array(ocr_data)[:, 2], q_val)

        return (
            [*filter(lambda data: data[2] >= cutout_prob, ocr_data)] if len(ocr_data) > safe_amount else ocr_data
        )

    def do_ocr(self):
        recognized_data = (
            self.drop_incidental(self.recognize_text()) if self.large_image else self.recognize_text()
        )

        for (bbox, text, prob) in recognized_data:
            if text not in self.text_data:
                self.text_data.append(text)
                print(f"Detected text: {text} (Probability: {prob:.2f})")

        self.image_of_text = bool(len(self.text_data))

        self.draw_result(recognized_data)

    def detect_text(self):
        if not self.large_image:
            self.image = self.make_square(self.make_square(self.image))

        self.enhance_grayscale()
        self.adapt_threshhold()
        self.noise_removal()

        if not self.large_image:
            self.erode_font()
            self.cover_scene()
            self.mosaic_enhanced()

        self.write_filtered_images()
        self.do_ocr()
