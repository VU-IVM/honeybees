# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging
import yaml


class Model:
    def __init__(
        self,
        current_time,
        timestep_length,
        config_path=None,
        n_timesteps=None,
        args=None,
    ):
        self.start_time = current_time
        self.timestep_length = timestep_length
        self.n_timesteps = n_timesteps
        if config_path is not None:
            self.config = self.setup_config(config_path)
        self.args = args
        self.logger = self.create_logger()
        self.logger.info("Initializing model")
        self.current_timestep = 0
        self.running = True

    @property
    def bounds(self):
        """Property returning the bounds of the current model as tuple

        Returns:
            tuple: xmin, xmax, ymin, ymax bounds of the model

        """
        return self.xmin, self.xmax, self.ymin, self.ymax

    @property
    def xmin(self):
        """Get model xmin

        Returns:
            float: xmin
        """
        return self.area.geoms["xmin"]

    @property
    def xmax(self):
        """Get model xmax

        Returns:
            float: xmax
        """
        return self.area.geoms["xmax"]

    @property
    def ymin(self):
        """Get model ymin

        Returns:
            float: ymin
        """
        return self.area.geoms["ymin"]

    @property
    def ymax(self):
        """Get model ymax

        Returns:
            float: ymax
        """
        return self.area.geoms["ymax"]

    @property
    def current_time_fmt(self):
        if self.timestep_length.days >= 1:
            dateformat = "%d %b %Y"
        else:
            dateformat = "%d %b %Y %H:%M"
        formatted_date = self.current_time.strftime(dateformat)
        if formatted_date.startswith(
            "0"
        ):  # Windows cannot handle %-d, so this is a safe way to remove the preceding 0
            formatted_date = formatted_date[1:]
        return formatted_date

    @property
    def current_time(self):
        """
        Returns:
            datetime.datetime: current model time
        """
        return self.start_time + self.current_timestep * self.timestep_length

    @property
    def end_time(self):
        """
        Returns:
            datetime.datetime: end time of the model
        """
        return self._current_time + self.n_timesteps * self.timestep_length

    @property
    def current_timestep(self):
        """
        Returns:
            int: current model timestep
        """
        return self._current_timestep

    @current_timestep.setter
    def current_timestep(self, v):
        self._current_timestep = v

    def create_logger(self):
        logger = logging.getLogger("honeybees")

        if (
            self.config
            and "logging" in self.config
            and "loglevel" in self.config["logging"]
        ):
            loglevel = self.config["logging"]["loglevel"]
        else:
            loglevel = "INFO"
        logger.setLevel(logging.getLevelName(loglevel))

        if (
            self.config
            and "logging" in self.config
            and "logfile" in self.config["logging"]
        ):
            logfile = self.config["logging"]["logfile"]
        else:
            logfile = "honeybees.log"
        file_handler = logging.FileHandler(logfile, mode="w")
        logger.addHandler(file_handler)

        formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
        file_handler.setFormatter(formatter)

        return logger

    def setup_config(self, config):
        if config is None:
            return None
        elif isinstance(config, dict):
            return config
        elif isinstance(config, str):
            with open(config, "r") as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
            return config
        else:
            raise ValueError(
                f"config should be a dict or a path to a yaml file, not {type(config)}"
            )

    def parse_step_str(self, step_string):
        if step_string == "day":
            new_time = self.current_time + timedelta(days=1)
            difference = new_time - self.current_time
            n = int(difference / self.timestep_length)
        elif step_string == "week":
            new_time = self.current_time + timedelta(days=7)
            difference = new_time - self.current_time
            n = int(difference / self.timestep_length)
        elif step_string == "month":
            new_time = self.current_time + relativedelta(months=1)
            difference = new_time - self.current_time
            n = int(difference / self.timestep_length)
        elif step_string == "year":
            new_time = self.current_time + relativedelta(years=1)
            if isinstance(self.timestep_length, relativedelta):
                assert self.timestep_length.years == 1
                n = 1
            else:
                difference = new_time - self.current_time
                n = int(difference / self.timestep_length)
        elif step_string == "decade":
            new_time = self.current_time + relativedelta(years=10)
            if isinstance(self.timestep_length, relativedelta):
                assert self.timestep_length.years == 1
                n = 10
            else:
                difference = new_time - self.current_time
                n = int(difference / self.timestep_length)
        elif step_string == "century":
            new_time = self.current_time + relativedelta(years=100)
            if isinstance(self.timestep_length, relativedelta):
                assert self.timestep_length.years == 1
                n = 100
            else:
                difference = new_time - self.current_time
                n = int(difference / self.timestep_length)
        else:
            raise ValueError(f"{step_string} not a known step_size")
        return n

    def step(self, step_size=1, report=True):
        if isinstance(step_size, str):
            n = self.parse_step_str(step_size)
        else:
            n = step_size
        self.current_timestep += 1

        assert isinstance(n, int) and n > 0
        for _ in range(n):
            # t0 = time()
            # print('Simulating agent behavior')
            self.agents.step()
            # t1 = time()
            if report:
                self.reporter.step()
            # t2 = time()
            # print('\tstep time', t1- t0)
            # print('\treport time', t2 - t1)

    def run(self, report=True):
        for _ in range(self.n_timesteps):
            self.step(report=report)
        self.report()

    def report(self):
        return self.reporter.report()
