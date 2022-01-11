def contrast(background, text):
    background = relative_luminance(background)
    text = relative_luminance(text)
    return max((background + 0.05) / (text + 0.05), (text + 0.05) / (background + 0.05))


def relative_luminance(rgb):
    """
    Calculates relative luminance for a color in RGB scale.
    sqrt(0.299 * R^2 + 0.587 * G^2 + 0.114 * B^2)
    """
    odds = [0.2126, 0.7152, 0.0722]  # sensitivity of the human eye to individual components of light (R,G,B)
    return sum(n1 * n2 for n1, n2 in zip(odds, list(map(linear_value, rgb))))


def linear_value(color):
    if color <= 0.03928:
        return color / 12.92
    return ((color + 0.055) / 1.055) ** 2.4