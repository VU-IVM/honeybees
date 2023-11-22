# -*- coding: utf-8 -*-
import colorsys
import math
import numpy as np


class Artists:
    """Test"""

    def __init__(self, model):
        self.model = model

    def draw_global(self):
        return {
            "type": "shape",
            "shape": "polygon",
            "filled": False,
            "color": "Black",
            "edge": True,
        }

    def select_latest_reporter_values(self, report_group, name):
        return self.model.reporter.variables["country"][name][-1]

    def add_alpha_to_hex_color(self, hex_color, alpha):
        decimal_alpha = int(alpha * 255)
        alpha_hex = hex(decimal_alpha).replace(
            "0x", ""
        )  # all hex values are prefixed with '0x'
        if len(alpha_hex) == 1:  # value has 1 number
            alpha_hex = "0" + alpha_hex
        return hex_color + alpha_hex

    def get_alpha(self, value, min, max):
        alpha = (value - min) / (max - min)
        if alpha < 0:
            alpha = 0
        if alpha > 1:
            alpha = 1
        return alpha

    def rgb_to_hex(self, rgb):
        def clamp(x):
            x = int(x * 255)
            return max(0, min(x, 255))

        hex_color = f"#{clamp(rgb[0]):02x}{clamp(rgb[1]):02x}{clamp(rgb[2]):02x}"
        if len(rgb) == 4:
            hex_color += f"{clamp(rgb[3]):02x}"
        return hex_color

    def hex_to_rgb(self, h):
        if h.startswith("#"):
            h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def generate_distinct_colors(self, n, mode):
        hsv_tuples = [(x * 1.0 / n, 0.5, 0.5) for x in range(n)]
        if mode == "hsv":
            return hsv_tuples
        rgb_tuples = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
        if mode == "rgb":
            return rgb_tuples
        if mode == "hex":
            return [self.rgb_to_hex(rgb) for rgb in rgb_tuples]
        else:
            raise NotImplementedError

    def generate_discrete_colors(self, n, color, mode, min_alpha=0):
        alphas = np.linspace(min_alpha, 1, n)
        if mode == "hex":
            return [self.add_alpha_to_hex_color(color, alpha) for alpha in alphas]
        elif mode == "rgb":
            return [(color[0], color[1], color[2], alpha) for alpha in alphas]
        else:
            raise NotImplementedError

    def round_to_n_significant_digits(self, value, n):
        if value == 0:
            return 0
        else:
            if math.isinf(value) or math.isnan(value):
                return value
            else:
                return round(value, n - int(math.floor(math.log10(abs(value)))) - 1)

    def draw_river(self):
        return {"type": "shape", "shape": "line", "color": "Blue"}

    def get_background(self):
        return None

    def get_background_variables(self):
        return None


if __name__ == "__main__":
    artist = Artists(None)
    print(artist.generate_distinct_colors(10, mode="hex"))
