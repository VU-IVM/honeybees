from datetime import date
import numpy as np
from dateutil.relativedelta import relativedelta

from honeybees.model import Model
from honeybees.area import Area
from honeybees.reporter import Reporter
from honeybees.agents import AgentBaseClass


class People(AgentBaseClass):
    def __init__(self, model, agents):
        self.n = 1000
        self.model = model
        self.agents = agents
        self.age = np.random.randint(0, 100, self.n)
        self.locations = np.zeros((self.n, 2), dtype=np.float32)
        self.update_locations()

    def update_locations(self):
        self.locations[:, 0] = np.random.uniform(
            self.model.xmin, self.model.xmax, self.n
        )
        self.locations[:, 1] = np.random.uniform(
            self.model.ymin, self.model.ymax, self.n
        )

    def step(self):
        self.age += 1
        self.update_locations()


class Agents(AgentBaseClass):
    def __init__(self, model):
        self.people = People(model, self)

    def step(self):
        self.people.step()


class ABMModel(Model):
    def __init__(self, config_path, study_area, args=None):
        self.area = Area(self, study_area)
        self.agents = Agents(self)

        current_time = date(2020, 1, 1)
        timestep_length = relativedelta(years=1)
        n_timesteps = 10

        Model.__init__(
            self,
            current_time,
            timestep_length,
            config_path,
            args=args,
            n_timesteps=n_timesteps,
        )

        self.reporter = Reporter(self)


if __name__ == "__main__":
    config_path = "examples/config.yml"
    study_area = {"xmin": -10, "xmax": 10, "ymin": -10, "ymax": 10}
    model = ABMModel(config_path, study_area)
