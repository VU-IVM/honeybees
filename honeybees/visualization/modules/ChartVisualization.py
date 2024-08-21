# -*- coding: utf-8 -*-
"""
Chart Module
============

Module for drawing live-updating line charts using Charts.js

"""

import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from honeybees.visualization.ModularVisualization import VisualizationElement


class ChartModule(VisualizationElement):
    """Each chart can visualize one or more model-level series as lines
     with the data value on the Y axis and the step number as the X axis.

    At the moment, each call to the render method returns a list of the most
    recent values of each series.

    Attributes:
        series: A list of dictionaries containing information on series to
                plot. Each dictionary must contain (at least) the "name" and
                "color" keys. The "name" value must correspond to a
                model-level series collected by the model's DataCollector, and
                "color" must have a valid HTML color.
        canvas_height, canvas_width: The width and height to draw the chart on
                                     the page, in pixels. Default to 200 x 500
        data_collector_name: Name of the DataCollector object in the model to
                             retrieve data from.
        template: "chart_module.html" stores the HTML template for the module.


    Example:
        schelling_chart = ChartModule([{"name": "happy", "color": "Black"}],
                                      data_collector_name="datacollector")

    TODO:
        Have it be able to handle agent-level variables as well.

        More Pythonic customization; in particular, have both series-level and
        chart-level options settable in Python, and passed to the front-end
        the same way that "color" is currently.

    """

    package_includes = ["Chart.min.js", "ChartModule.js"]

    def __init__(self, series, canvas_height=200, canvas_width=500):
        """
        Create a new line chart visualization.

        Args:
            series: A list of dictionaries containing series names and
                    HTML colors to chart them in, e.g.
                    [{"name": "happy", "color": "Black"},]
            canvas_height, canvas_width: Size in pixels of the chart to draw.
            data_collector_name: Name of the DataCollector to use.
        """
        self.series = series
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width

        # if first series has a color, assert all series have a color
        # if first series has no color, assure remaining series have no color and
        # assign colors from color wheel
        if self.series:
            if "color" in self.series[0]:
                assert all("color" in series for series in self.series)
            else:
                assert all("color" not in series for series in self.series)
                series_length = len(self.series)
                color_map = plt.get_cmap("gist_rainbow")
                for i, series in enumerate(self.series):
                    color = mcolors.rgb2hex(color_map(i / series_length))
                    series["color"] = color

        series_json = json.dumps(self.series)
        new_element = "new ChartModule({}, {},  {})"
        new_element = new_element.format(series_json, canvas_width, canvas_height)
        self.js_code = "elements.push(" + new_element + ");"

        self.reset()

    def render(self, model, update):
        if not update:
            self.current_chart_x_index = 0

        xs = model.reporter.timesteps[self.current_chart_x_index :]
        if model.timestep_length.days >= 1:
            dateformat = "%d %b %Y"
        else:
            dateformat = "%d %b %Y %H:%M"
        xs = [x.strftime(dateformat) for x in xs]

        ys = []
        for s in self.series:
            name = s["name"]
            yvar = model.reporter.variables[name]
            if "ID" in s:
                yvar = yvar[s["ID"]]
            yvar = yvar[self.current_chart_x_index :]
            ys.append(yvar)  # Latest values
            if len(xs) != len(yvar):
                if len(yvar) == 0:
                    model.logger.info(
                        f"Variable '{name}' cannot be shown in chart because it is not found in reporter."
                    )
                else:
                    model.logger.info(
                        f"Variable '{name}' cannot be shown in chart for some timesteps because it is not found in reporter for all requested timesteps."
                    )

        self.current_chart_x_index += len(xs)

        return {"xs": xs, "ys": ys}

    def reset(self):
        self.current_chart_x_index = 0
