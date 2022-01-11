from typing import Tuple, Union, List

from PIL import ImageOps
from PIL.Image import Image
from PIL.ImageDraw import ImageDraw

from framework.screenshot.draw_arrows import Direction, CoordinateArrow

RED = (255, 0, 0)
BLACK = (0, 0, 0)

SAFE_MARGIN = 200
MARGIN = 10
DISTANCE = 5  # Distance for found pixel near element


class Draw:

    def __init__(self, coordinates: Union[Tuple[int, int, int, int], List[int]], image: Image):
        self.x1, self.y1, self.x2, self.y2 = coordinates
        self.image = image
        self.image_width, self.image_height = image.size

    def draw(self):
        """
        Draws a line with correction for free space near element.
        """
        color = self._get_color_contour()
        print(self)
        coordinates, direction = self._check_free_space()

        draw = ImageDraw(self.image)
        draw.rectangle(((self.x1, self.y1), (self.x2, self.y2)), outline=color, width=4)

        if coordinates is not None:
            arrow = CoordinateArrow().get_arrow_coordinate(coordinates, 150, 50, 10, direction)
            for line in arrow:
                draw.line(line, fill=color, width=4)
        del draw
        image = ImageOps.expand(self.image, border=3,
                                fill=BLACK)  # TODO: fix `Expected type 'int', got 'Tuple[int, int, int]' instead `
        return image

    def _get_color_contour(self):
        """
        Changes the color of the outline depending on the environment of the element.
        """
        image = self.image.convert("RGB")
        for pixel in [(self.x1 - DISTANCE, self.y1),
                      (self.x1, self.y1 - DISTANCE),
                      (self.x2 + DISTANCE, self.y2),
                      (self.x2, self.y2 + DISTANCE)]:
            if not all([p >= 0 for p in pixel]) or not pixel[0] < self.image_width or not pixel[1] < self.image_height:
                continue
            elif self._check_color_range(image.getpixel(pixel)):
                return BLACK
        return RED

    @staticmethod
    def _check_color_range(color):
        min_range_color = 150
        max_range_color = 255
        return min_range_color <= color[0] <= max_range_color and \
               (0 <= color[1] <= min_range_color or 0 <= color[2] <= min_range_color)

    def _check_free_space(self) -> Union[Tuple[Tuple[int, int], Direction],
                                         Tuple[Tuple[int, float], Direction],
                                         Tuple[Tuple[float, int], Direction],
                                         Tuple[None, None]]:
        """
        Searches for free space near an item, for drawing arrow.
        """

        left, right = SAFE_MARGIN, self.image_width - SAFE_MARGIN
        top, bottom = SAFE_MARGIN, self.image_height - SAFE_MARGIN

        if self.x1 >= left and self.y2 <= bottom:
            return (self.x1 - MARGIN, self.y2 + MARGIN), Direction.BOTTOM_LEFT
        elif self.x2 <= right and self.y1 >= top:
            return (self.x2 + MARGIN, self.y1 - MARGIN), Direction.TOP_RIGHT
        elif self.x1 >= left and self.y1 >= top:
            return (self.x1 - MARGIN, self.y1 - MARGIN), Direction.TOP_LEFT
        elif self.x2 <= right and self.y2 <= bottom:
            return (self.x2 + MARGIN, self.y2 + MARGIN), Direction.BOTTOM_RIGHT
        elif self.x1 >= left and not (self.y1 >= top and self.y2 <= bottom):
            return (self.x1 - MARGIN, (self.y1 + self.y2) / 2), Direction.LEFT
        elif not self.x1 >= left and self.y1 >= top:
            return ((self.x1 + self.x2) / 2, self.y1 - MARGIN), Direction.TOP
        elif self.x2 <= right and not (self.y1 >= top and self.y2 <= bottom):
            return (self.x2 + MARGIN, (self.y1 + self.y2) / 2), Direction.RIGHT
        elif not self.x2 <= right and self.y2 <= bottom:
            return ((self.x1 + self.x2) / 2, self.y2 + MARGIN), Direction.BOTTOM
        return None, None