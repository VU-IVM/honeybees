# -*- coding: utf-8 -*-
"""This module is used to report data to the disk and to extract data for visualisation. After initialization of the reporter in the model, the :meth:`honeybees.report.Reporter.step` method is called every timestep, which can obtain data from the agents, and report to disk or save the data for visualiation or writing to disk once the model is finished. The variables to be reported can be configured in the config file. All data is saved to the report folder by default.

In the configuration file you can specify which data should be reported. In this file you can configure which data should be saved from the model in the `report` folder. This should be formatted as follows:

 - **report**:
    - **name**: name of the folder to which the data is saved.
        - **type**: agent type e.g., farmer. Should be identical to attribute name in Agents class.
        - **function**: whether to use a function to parse the data. 'null' means the data is saved literally, 'mean' takes the mean etc. Options are sum/mean.
        - **varname**: attribute name of variable in agent class.
        - **format**: format to save to. Can be 'csv' to save to csv-file per timestep, 'npy' to save in NumPy binary format, or 'npz' to save in NumPy compressed binary format.
        - **initial_only**: if true only save the data for the first timestep.
        - **save**: save variable in model run, or export, or both (save/save+export/export).
    - **name2**:
        - ...
        - ...
    - **...**:
        - ...
        - ...
"""

import re
from collections.abc import Iterable
import os
import numpy as np
import pandas as pd
from operator import attrgetter
from numba import njit
from math import isinf
from copy import deepcopy
import zarr
from numcodecs import Blosc
from typing import Union, Any

zstd_compressor = Blosc(cname="zstd", clevel=3, shuffle=Blosc.BITSHUFFLE)


def create_time_array(start, end, timestep, conf):
    if "frequency" not in conf:
        frequency = {"every": "day"}
    else:
        frequency = conf["frequency"]
    if "every" in frequency:
        every = frequency["every"]
        time = []
        current_time = start
        while current_time <= end:
            if every == "year":
                if (
                    frequency["month"] == current_time.month
                    and frequency["day"] == current_time.day
                ):
                    time.append(current_time)
            elif every == "month":
                if frequency["day"] == current_time.day:
                    time.append(current_time)
            elif every == "day":
                time.append(current_time)
            current_time += timestep
        return time
    elif frequency == "initial":
        return [start]
    elif frequency == "final":
        return [end]
    else:
        raise ValueError(f"Frequency {frequency} not recognized.")


class Reporter:
    """This class is used to report data to disk or for visualisation. The `step` method is called each timestep from the model.

    Args:
        model: The model.
        subfolder: Optional name of the subfolder to be reported in. By default the report folder from the configuration file is used (general:report_folder).
    """

    def __init__(self, model, folder: str) -> None:
        self.model = model
        if not hasattr(self.model, "agents"):  # ensure agents exist
            raise NameError(
                "Attribute agents of model does not exists. This most likely means that the reporter was created before the agents."
            )

        self.variables = {}
        self.timesteps = []
        self.export_folder = folder

        if (
            self.model.config is not None
            and "report" in self.model.config
            and self.model.config["report"] is not None
        ):
            self.enabled = True
            for name, conf in self.model.config["report"].items():
                if conf["format"] == "zarr":
                    filepath = os.path.join(self.export_folder, name + ".zarr.zip")
                    ds = zarr.open_group(filepath, mode="w")

                    time = create_time_array(
                        start=self.model.current_time,
                        end=self.model.end_time,
                        timestep=self.model.timestep_length,
                        conf=conf,
                    )

                    ds.create_dataset(
                        "time",
                        data=time,
                        dtype="datetime64[ns]",
                    )
                    ds["time"].attrs["_ARRAY_DIMENSIONS"] = ["time"]

                    conf["_file"] = ds
                    conf["_time_index"] = time
        else:
            self.enabled = False

        self.step()

    def check_value(self, value: Any):
        """Check whether the value is a Python integer or float, and is not infinite.

        Args:
            value: The value to be checked.
        """
        if not (
            isinstance(value, (int, float)) or value is None
        ):  # check item is normal Python float or int. This is required to succesfully convert to JSON.
            raise ValueError(
                f"value {value} of type {type(value)} is not Python float or int"
            )
        if isinstance(value, float):
            assert not isinf(value)

    def export_value(self, name: str, value: np.ndarray, conf: dict) -> None:
        """Exports an array of values to the export folder.

        Args:
            name: Name of the value to be exported.
            value: The array itself.
            conf: Configuration for saving the file. Contains options such a file format, and whether to export the array in this timestep at all.
        """
        if value is None:
            return None
        if "format" not in conf:
            raise ValueError(
                f"Export format must be specified for {name} in config file (npy/npz/csv/xlsx)."
            )
        if conf["format"] == "zarr":
            ds = conf["_file"]
            if name not in ds:
                if isinstance(value, (float, int)):
                    shape = (ds["time"].size,)
                    chunks = (1,)
                    compressor = None
                    dtype = type(value)
                    array_dimensions = ["time"]
                else:
                    shape = (ds["time"].size, value.size)
                    chunks = (1, value.size)
                    compressor = zstd_compressor
                    dtype = value.dtype
                    array_dimensions = ["time", "agents"]
                if dtype in (float, np.float32, np.float64):
                    fill_value = np.nan
                elif dtype in (int, np.int32, np.int64):
                    fill_value = -1
                else:
                    raise ValueError(
                        f"Value {dtype} of type {type(dtype)} not recognized."
                    )
                ds.create_dataset(
                    name,
                    shape=shape,
                    chunks=chunks,
                    dtype=dtype,
                    compressor=compressor,
                    fill_value=fill_value,
                )
                ds[name].attrs["_ARRAY_DIMENSIONS"] = array_dimensions
            index = conf["_time_index"].index(self.model.current_time)
            if value.size < ds[name][index].size:
                print("Padding array with NaNs or -1 - temporary solution")
                value = np.pad(
                    value,
                    (0, ds[name][index].size - value.size),
                    mode="constant",
                    constant_values=np.nan
                    if value.dtype in (float, np.float32, np.float64)
                    else -1,
                )
            ds[name][index] = value
        else:
            folder = os.path.join(self.export_folder, name)
            os.makedirs(folder, exist_ok=True)
            fn = f"{self.timesteps[-1].isoformat().replace('-', '').replace(':', '')}"
            if conf["format"] == "npy":
                fn += ".npy"
                fp = os.path.join(folder, fn)
                np.save(fp, value)
            elif conf["format"] == "npz":
                fn += ".npz"
                fp = os.path.join(folder, fn)
                np.savez_compressed(fp, data=value)
            elif conf["format"] == "csv":
                fn += ".csv"
                fp = os.path.join(folder, fn)
                if len(value) > 100_000:
                    self.model.logger.info(
                        f"Exporting {len(value)} items to csv. This might take a long time and take a lot of space. Consider using NumPy (compressed) binary format (npy/npz)."
                    )
                with open(fp, "w") as f:
                    f.write("\n".join([str(v) for v in value]))
            else:
                raise ValueError(f"{conf['format']} not recognized")

    def report_value(
        self, name: Union[str, tuple[str, Any]], value: Any, conf: dict
    ) -> None:
        """This method is used to save and/or export model values.

        Args:
            name: Name of the value to be exported.
            value: The array itself.
            conf: Configuration for saving the file. Contains options such a file format, and whether to export the data or save the data in the model.
        """
        if isinstance(value, list):
            value = [v.item() for v in value]
            for v in value:
                self.check_value(v)

        if "save" in conf:
            if conf["save"] not in ("save", "export"):
                raise ValueError(
                    f"Save type for {name} in config file must be 'save', 'save+export' or 'export')."
                )
            import warnings

            warnings.warn(
                "The `save` option is deprecated and will be removed in future versions. If you use 'save: export' the option can simply be removed (new default). If you use 'save: save', please replace with 'single_file: true'",
                DeprecationWarning,
            )
            if conf["save"] == "save":
                conf["single_file"] = True
            del conf["save"]

        if (
            "single_file" in conf
            and conf["single_file"] is True
            and conf["format"] != "zarr"  # for zarr, we always save per timestep
        ):
            try:
                if isinstance(name, tuple):
                    name, ID = name
                    if name not in self.variables:
                        self.variables[name] = {}
                    if ID not in self.variables[name]:
                        self.variables[name][ID] = []
                    self.variables[name][ID].append(value)
                else:
                    if name not in self.variables:
                        self.variables[name] = []
                    self.variables[name].append(value)
            except KeyError:
                raise KeyError(
                    f"Variable {name} not initialized. This likely means that an agent is reporting for a group that was not is not the reporter"
                )

        else:
            if "frequency" in conf and conf["frequency"] is not None:
                if conf["frequency"] == "initial":
                    if self.model.current_timestep == 0:
                        self.export_value(name, value, conf)
                elif conf["frequency"] == "final":
                    if self.model.current_timestep == self.model.n_timesteps:
                        self.export_value(name, value, conf)
                elif "every" in conf["frequency"]:
                    every = conf["frequency"]["every"]
                    if every == "year":
                        month = conf["frequency"]["month"]
                        day = conf["frequency"]["day"]
                        if (
                            self.model.current_time.month == month
                            and self.model.current_time.day == day
                        ):
                            self.export_value(name, value, conf)
                    elif every == "month":
                        day = conf["frequency"]["day"]
                        if self.model.current_time.day == day:
                            self.export_value(name, value, conf)
                    elif every == "day":
                        self.export_value(name, value, conf)
                    else:
                        raise ValueError(
                            f"Frequency every {conf['every']} not recognized (must be 'yearly', or 'monthly')."
                        )
                else:
                    raise ValueError(f"Frequency {conf['frequency']} not recognized.")
            else:
                self.export_value(name, value, conf)

    @staticmethod
    @njit(cache=True)
    def mean_per_ID(
        values: np.ndarray, group_ids: np.ndarray, n_groups: int
    ) -> np.ndarray:
        """Calculates the mean value per group.

        Args:
            values: Numpy array of values.
            group_ids: Group IDs for each value. Must be same size as values.
            n_groups: The total number of groups.

        Returns:
            mean_per_ID: The mean value for each of the groups.
        """
        assert values.size == group_ids.size
        size = values.size
        count_per_group = np.zeros(n_groups, dtype=np.int32)
        sum_per_group = np.zeros(n_groups, dtype=values.dtype)
        for i in range(size):
            group_id = group_ids[i]
            assert group_id < n_groups
            count_per_group[group_id] += 1
            sum_per_group[group_id] += values[i]
        return sum_per_group / count_per_group

    @staticmethod
    @njit(cache=True)
    def sum_per_ID(
        values: np.ndarray, group_ids: np.ndarray, n_groups: int
    ) -> np.ndarray:
        """Calculates the sum value per group.

        Args:
            values: Numpy array of values.
            group_ids: Group IDs for each value. Must be same size as values.
            n_groups: The total number of groups.

        Returns:
            sum_per_ID: The sum value for each of the groups.
        """
        assert values.size == group_ids.size
        size = values.size
        sum_per_group = np.zeros(n_groups, dtype=values.dtype)
        for i in range(size):
            group_id = group_ids[i]
            assert group_id < n_groups
            sum_per_group[group_id] += values[i]
        return sum_per_group

    def parse_agent_data(self, name: str, values: Any, agents, conf: dict) -> None:
        """This method is used to apply the relevant function to the given data.

        Args:
            name: Name of the data to report.
            values: Numpy array of values.
            agents: The relevant agent class.
            conf: Dictionary with report configuration for values.
        """
        function = conf["function"]
        if function is None or values is None:
            values = deepcopy(
                values
            )  # need to copy item, because values are passed without applying any a function.
            self.report_value(name, values, conf)
        else:
            function, *args = conf["function"].split(",")
            if function == "mean":
                value = np.mean(values)
                self.report_value(name, value, conf)
            elif function == "sum":
                value = np.sum(values)
                self.report_value(name, value, conf)
            elif function == "sample":
                sample = getattr(agents, "sample")
                value = values[sample]
                for s, v in zip(sample, value):
                    self.report_value((name, s), v, conf)
            elif function == "groupcount":
                for group in args:
                    group = int(group)
                    self.report_value(
                        (name, group), np.count_nonzero(values == group), conf
                    )
            else:
                raise ValueError(f"{function} function unknown")

    def extract_agent_data(self, name: str, conf: dict) -> None:
        """This method is used to extract agent data and apply the relevant function to the given data.

        Args:
            name: Name of the data to report.
            conf: Dictionary with report configuration for values.
        """
        agents = attrgetter(conf["type"])(self.model.agents)
        varname = conf["varname"]
        fancy_index = re.search(r"\[.*?\]", varname)
        if fancy_index:
            fancy_index = fancy_index.group(0)
            varname = varname.replace(fancy_index, "")

        try:
            values = getattr(agents, varname)
        except AttributeError:
            print(
                f"Trying to export '{varname}', but no such attribute exists for agent type '{conf['type']}'"
            )
            values = None

        if fancy_index:
            values = eval(f"values{fancy_index}")

        if "split" in conf and conf["split"]:
            for ID, admin_values in zip(agents.ids, values):
                self.parse_agent_data((name, ID), admin_values, agents, conf)
        else:
            self.parse_agent_data(name, values, agents, conf)

    def step(self) -> None:
        """This method is called every timestep. First appends the current model time to the list of times for the reporter. Then iterates through the data to be reported on and calls the extract_agent_data method for each of them."""
        self.timesteps.append(self.model.current_time)
        if self.enabled:
            for name, conf in self.model.config["report"].items():
                self.extract_agent_data(name, conf)

    def report(self) -> dict:
        """This method can be called to save the data that is currently saved in memory to disk."""
        report_dict = {}
        for name, values in self.variables.items():
            if isinstance(values, dict):
                df = pd.DataFrame.from_dict(values)
                df.index = self.timesteps
            elif isinstance(values[0], Iterable):
                df = pd.DataFrame.from_dict(
                    {k: v for k, v in zip(self.timesteps, values)}
                )
            else:
                df = pd.DataFrame(values, index=self.timesteps, columns=[name])
            if "format" not in self.model.config["report"][name]:
                raise ValueError(
                    f"Key 'format' not specified in config file for {name}"
                )
            export_format = self.model.config["report"][name]["format"]
            filepath = os.path.join(self.export_folder, name + "." + export_format)
            if export_format == "csv":
                df.to_csv(filepath)
            elif export_format == "xlsx":
                df.to_excel(filepath)
            elif export_format == "npy":
                np.save(filepath, df.values)
            elif export_format == "npz":
                np.savez_compressed(filepath, data=df.values)
            else:
                raise ValueError(f"save_to format {export_format} unknown")
        return report_dict
