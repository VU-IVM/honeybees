# -*- coding: utf-8 -*-
import math
from honeybees.visualization.ModularVisualization import VisualizationElement
import numpy as np
from PIL import Image
import base64
from io import BytesIO


class Canvas(VisualizationElement):
    package_includes = ["canvas.js"]
    portrayal_method = None

    def __init__(self, max_canvas_width, max_canvas_height, unit="degrees"):
        """
        Instantiate a new Canvas
        """
        self.max_canvas_width = max_canvas_width
        self.max_canvas_height = max_canvas_height
        self.unit = unit
        new_element = "new Simple_Continuous_Module({}, {})".format(
            self.max_canvas_width, self.max_canvas_height
        )
        self.js_code = "elements.push(" + new_element + ");"

    def get_canvas_size(self, model):
        horizontal_distance = abs(model.xmin - model.xmax)
        vertical_distance = abs(model.ymin - model.ymax)

        if self.unit == "degrees":
            lat = (model.ymax + model.ymin) / 2
            horizontal_distance *= math.cos(math.radians(lat))
        elif self.unit == "meters":
            pass
        else:
            raise ValueError("unit must be degrees or meters")

        scaling_factor_width = self.max_canvas_width / (horizontal_distance)
        maybe_height = (vertical_distance) * scaling_factor_width
        if maybe_height > self.max_canvas_height:
            height = self.max_canvas_height
            scaling_factor_height = self.max_canvas_height / (vertical_distance)
            width = (horizontal_distance) * scaling_factor_height
        else:
            height = maybe_height
            width = self.max_canvas_width

        # +30 for legend
        if width + 30 < self.max_canvas_width:
            width += 30
        else:
            height /= self.max_canvas_width / width
            width = self.max_canvas_width

        return width, height

    def convert_lon_to_x(self, x, model):
        assert not np.isnan(x)
        return (x - model.area.geoms["xmin"]) / (
            model.area.geoms["xmax"] - model.area.geoms["xmin"]
        )

    def convert_lat_to_y(self, y, model):
        assert not np.isnan(y)
        return (y - model.area.geoms["ymin"]) / (
            model.area.geoms["ymax"] - model.area.geoms["ymin"]
        )

    def get_portrayal(self, artist, geography_kwargs):
        if geography_kwargs:
            portrayal = artist(**geography_kwargs)
        else:
            try:
                portrayal = artist()
            except TypeError as e:
                raise TypeError(
                    e.__repr__()
                    + "\nIs the missing argument specified in your config file?"
                )
        return portrayal

    def parse_linestring(self, coordinates, artist, geography_kwargs, model):
        portrayal = self.get_portrayal(artist, geography_kwargs)
        portrayal["lines"] = []
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]
        portrayal["lines"].append(
            {
                "xs": [self.convert_lon_to_x(lon, model) for lon in lons],
                "ys": [self.convert_lat_to_y(lat, model) for lat in lats],
            }
        )
        return portrayal

    def parse_multilinestring(self, coordinates, artist, geography_kwargs, model):
        portrayal = self.get_portrayal(artist, geography_kwargs)
        portrayal["lines"] = []
        for line in coordinates:
            lons = [coord[0] for coord in line]
            lats = [coord[1] for coord in line]
            portrayal["lines"].append(
                {
                    "xs": [self.convert_lon_to_x(lon, model) for lon in lons],
                    "ys": [self.convert_lat_to_y(lat, model) for lat in lats],
                }
            )
        return portrayal

    def parse_multipolygon(self, coordinates, artist, geography_kwargs, model):
        portrayal = self.get_portrayal(artist, geography_kwargs)
        portrayal["rings"] = []
        for polygon in coordinates:
            for ring in polygon:
                lons = [coord[0] for coord in ring]
                lats = [coord[1] for coord in ring]
                portrayal["rings"].append(
                    {
                        "xs": [self.convert_lon_to_x(lon, model) for lon in lons],
                        "ys": [self.convert_lat_to_y(lat, model) for lat in lats],
                    }
                )
        return portrayal

    def parse_polygon(self, coordinates, artist, geography_kwargs, model):
        portrayal = self.get_portrayal(artist, geography_kwargs)
        portrayal["rings"] = []
        for ring in coordinates:
            lons = [coord[0] for coord in ring]
            lats = [coord[1] for coord in ring]
            portrayal["rings"].append(
                {
                    "xs": [self.convert_lon_to_x(lon, model) for lon in lons],
                    "ys": [self.convert_lat_to_y(lat, model) for lat in lats],
                }
            )
        return portrayal

    def parse_geojson(self, feature, *args, **kwargs):
        if "geometry" in feature:
            geometry = feature["geometry"]
        else:
            geometry = feature
        if geometry["type"] == "MultiPolygon":
            return self.parse_multipolygon(geometry["coordinates"], *args, **kwargs)
        elif geometry["type"] == "Polygon":
            return self.parse_polygon(geometry["coordinates"], *args, **kwargs)
        elif geometry["type"] == "LineString":
            return self.parse_linestring(geometry["coordinates"], *args, **kwargs)
        elif geometry["type"] == "MultiLineString":
            return self.parse_multilinestring(geometry["coordinates"], *args, **kwargs)
        else:
            raise NotImplementedError

    def get_static_space_state(self, model):
        if not hasattr(self, "static_space_state"):
            self.static_space_state = {}
            if (
                "draw_geography" in model.config["draw"]
                and model.config["draw"]["draw_geography"]
            ):
                for name, geography_kwargs in model.config["draw"][
                    "draw_geography"
                ].items():
                    used_IDs = set()
                    artist = getattr(model.artists, f"draw_{name}")
                    try:
                        geojsons = model.area.geoms[name]
                    except KeyError:
                        raise KeyError(
                            f"{name} geom not available in model.area.geoms. Did you pass it as a key to study_area?"
                        )

                    type_static_state_space = {}
                    if isinstance(geojsons, (list, tuple)):
                        for geojson in geojsons:
                            assert isinstance(geojson, dict)
                            if "properties" not in geojson:
                                raise ValueError(
                                    f"Geojson for {name} has not properties"
                                )
                            if "id" not in geojson["properties"]:
                                raise ValueError(f"Geojson for {name} has not ID")
                            ID = geojson["properties"]["id"]
                            if ID in used_IDs:
                                raise ValueError(
                                    f"ID is already used for drawing {name}. Each geojson must have a unique ID."
                                )
                            else:
                                used_IDs.add(ID)
                            type_static_state_space[ID] = self.parse_geojson(
                                geojson, artist, geography_kwargs, model
                            )

                    elif isinstance(geojsons, dict):
                        geojson = geojsons  # only 1 geojson available
                        if "properties" in geojson and "id" in geojson["properties"]:
                            ID = geojsons[ID]
                        else:
                            ID = None
                        type_static_state_space[ID] = self.parse_geojson(
                            geojson, artist, geography_kwargs, model
                        )
                    else:
                        raise ValueError

                    self.static_space_state[name] = type_static_state_space
            return self.static_space_state
        else:
            return self.static_space_state

    def get_agents_portrayals(
        self, model, artist, artist_kwargs, agent_subclass_id, agent_space_state, agents
    ):
        if artist_kwargs is None:
            artist_kwargs = {}
        locations = agents.locations.data
        if isinstance(locations, tuple):
            portrayal = artist(model, agents, **artist_kwargs)
            portrayal["x"] = self.convert_lon_to_x(locations[0], model)
            portrayal["y"] = self.convert_lat_to_y(locations[1], model)
            agent_space_state[f"{agent_subclass_id}"] = portrayal
        elif isinstance(locations, np.ndarray):
            artist_kwargs_to_pass = dict(artist_kwargs)
            if "draw_every_nth" in artist_kwargs_to_pass:
                draw_every_nth = artist_kwargs_to_pass.pop("draw_every_nth")
            else:
                draw_every_nth = 1
            agents_to_draw = np.arange(0, agents.n, draw_every_nth)
            if agents_to_draw.size > 100_000:
                print(
                    f"Drawing {agents_to_draw.size} agents. This might take a while. Consider setting `draw_every_nth_agent` to reduce the number of agents drawn. (This warning is displayed because more than 100.000 agents are to be drawn.)"
                )
            for idx in agents_to_draw:
                portrayal = artist(model, agents, idx, **artist_kwargs_to_pass)
                portrayal["x"] = self.convert_lon_to_x(locations[idx, 0], model)
                portrayal["y"] = self.convert_lat_to_y(locations[idx, 1], model)
                agent_space_state[f"{agent_subclass_id}_{idx}"] = (
                    portrayal  # converting to python int, as this is JSON serializable
                )
        else:
            raise ValueError(
                f"locations property of agent class {type(agents).__name__} must be tuple or (n, 2) Numpy array with locations"
            )

        return agent_space_state

    def render(self, model, update):
        agent_space_state = {}
        if model.config["draw"]["draw_agents"]:
            for agent_type, artist_kwargs in model.config["draw"][
                "draw_agents"
            ].items():
                artist_name = f'draw_{agent_type.replace(".", "_")}'
                try:
                    artist = getattr(model.artists, artist_name)
                except AttributeError:
                    raise AttributeError(
                        f"{agent_type} specified in initialization file has no corresponding method draw function {artist_name} in {model.artists}"
                    )
                if "." in agent_type:
                    agent_class, agent_subclass = agent_type.split(".")
                    agent_class = getattr(model.agents, agent_class)
                    agent_subclass = getattr(agent_class, agent_subclass)
                    for agent_subclass_id, agents in agent_subclass.items():
                        agent_space_state = self.get_agents_portrayals(
                            model=model,
                            artist=artist,
                            artist_kwargs=artist_kwargs,
                            agent_subclass_id=agent_subclass_id,
                            agent_space_state=agent_space_state,
                            agents=agents,
                        )
                else:
                    agents = getattr(model.agents, agent_type)
                    agent_space_state = self.get_agents_portrayals(
                        model=model,
                        artist=artist,
                        artist_kwargs=artist_kwargs,
                        agent_subclass_id="",
                        agent_space_state=agent_space_state,
                        agents=agents,
                    )

        space_state = self.get_static_space_state(model)
        space_state["agents"] = agent_space_state

        space_state_list = []
        background = model.artists.get_background()
        if background is not None:
            background, legend = background
            if isinstance(background, np.ndarray):
                img = Image.fromarray(background, mode="RGBA")
                buffer = BytesIO()
                img.save(buffer, format="PNG")

                space_state_list.append(
                    {
                        "type": "background",
                        "ysize": background.shape[0],
                        "xsize": background.shape[1],
                        "img": "data:image/png;base64,"
                        + base64.b64encode(buffer.getvalue()).decode("utf-8"),
                    }
                )
            else:
                raise NotImplementedError

            # legend for the background
            if legend["type"] == "colorbar":
                space_state_list.append(
                    {
                        "type": "colorbar",
                        "location": "right",
                        "min": legend["min"],
                        "max": legend["max"],
                        "unit": legend["unit"],
                        "color_min": model.artists.add_alpha_to_hex_color(
                            legend["color"], legend["min_colorbar_alpha"]
                        ),
                        "color_max": legend["color"] + "FF",  # hex 255
                    }
                )
            elif legend["type"] == "legend":
                assert "labels" in legend
                legend["location"] = "right"
                space_state_list.append(legend)
            else:
                raise NotImplementedError

        background_variables = model.artists.get_background_variables()
        if background_variables:
            space_state_list.append(
                {
                    "type": "background options",
                    "options": background_variables,
                    "currentselection": (
                        model.artists.background_variable
                        if hasattr(model.artists, "background_variable")
                        else None
                    ),
                }
            )

        # legend for the agents
        if hasattr(model.artists, "legend"):
            space_state_list.append(
                {
                    "type": "legend",
                    "location": "left",
                    "labels": model.artists.legend,
                }
            )

        for type_, type_portrayals in space_state.items():
            try:
                updater = getattr(model.artists, f"update_{type_}")
            except AttributeError:
                pass
            else:
                for ID, portrayal in type_portrayals.items():
                    updater(ID, portrayal)
            for portrayal in type_portrayals.values():
                assert isinstance(portrayal, dict)
                space_state_list.append(portrayal)

        return {"size": self.get_canvas_size(model), "draw": space_state_list}
