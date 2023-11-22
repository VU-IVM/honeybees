# -*- coding: utf-8 -*-
import numpy as np


class AgentBaseClass:
    def __init__(self):
        pass

    @property
    def activation_order_random(self):
        """Returns containing all agent ids in random order.

        Returns:
            np.array: agent ids in random order
        """
        activation_order = np.arange(0, self.n, 1, dtype=np.int32)
        np.random.shuffle(activation_order)
        return activation_order

    def initiate_agents(self):
        raise NotImplementedError

    def step(self):
        raise NotImplementedError(f"step function not implemented in {self}")
