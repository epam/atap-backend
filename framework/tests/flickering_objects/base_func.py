import numpy as np
from PIL import Image


def full_duration(path: str):
    """ Calculate gif duration.

    """
    img = Image.open(path)
    img.seek(0)
    duration = []
    while True:
        try:
            duration.append(img.info["duration"])
            img.seek(img.tell() + 1)
        except EOFError:
            return duration


def fps(path: str):
    """ Returns the average framerate of a PIL Image object """
    return Image.open(path).n_frames / (sum(full_duration(path)) / 1000)


def frames_sec(path: str):
    """
    Quantity frames per first second.
    This method used because frames can have different duration on frames
    """
    map_secs = full_duration(path)
    time = 0
    count = 0
    for e in map_secs:
        if time >= 1000:
            break
        time += e
        count += 1
    return count


def path_frames_sec(path: str):
    """ Returns path to first and last frame of first sec"""
    fr = frames_sec(path)
    with Image.open(path) as im:
        im.seek(0)
        path_frame0 = path.replace(path[-4:], "_frame0.png")
        im.save(path_frame0, **im.info)

        im.seek(fr - 1)
        path_frame_last = path.replace(path[-4:], f"_frame{im.tell()}.png")
        im.save(path_frame_last, **im.info)

    return [path_frame0, path_frame_last]


def calculation(num1, num2, percent_threshold):
    if num1 == num2:
        return False
    if num1 == 0:
        num1 = 1
    if num2 == 0:
        num2 = 1
    return ((num2 / num1) * 100) > percent_threshold


def black2white(path: str):
    colors = np.unique(Image.open(path).convert('1'), axis=0)
    black = 0
    white = 0
    for color in colors.flat:
        if color:
            white += 1
        else:
            black += 1
    return [black, white, path]
