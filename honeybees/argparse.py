# -*- coding: utf-8 -*-
import argparse
from honeybees import __name__

parser = argparse.ArgumentParser(
    description=f"{__name__.title()} is a package for high-speed geographical agent-based modelling in Python"
)
parser.add_argument(
    "--GUI",
    dest="GUI",
    action="store_true",
    help="The model can be run with or without a visual interface. The visual interface is useful to display the results in real-time while the model is running and to better understand what is going on. You can simply start or stop the model with the click of a buttion, or advance the model by an `x` number of timesteps. However, the visual interface is much slower than running the model without it.",
)
parser.set_defaults(GUI=False)
parser.add_argument(
    "--no-browser",
    dest="browser",
    action="store_false",
    help="Do not open browser when running the model. This option is, for example, useful when running the model on a server, and you would like to remotely access the model.",
)
parser.set_defaults(browser=True)
default_port = 8521
parser.add_argument(
    "--port",
    dest="port",
    type=int,
    default=8521,
    help=f"Port used for display environment (default: {default_port})",
)
