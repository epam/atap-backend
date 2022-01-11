from typing import Optional, Union


def analyze_histogram(colors_histogram: Optional[Union[tuple, list]], flag=True) -> Optional[list]:
    if not colors_histogram:
        return
    histogram = sorted(colors_histogram, reverse=True)
    if flag:
        histogram = [h for h in histogram if h >= 0.15 * histogram[0]]
    return histogram
