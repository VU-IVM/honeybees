# -*- coding: utf-8 -*-


class Area:
    def __init__(self, model, study_area):
        """ """
        self.model = model
        self.geoms = study_area
        assert "xmin" in self.geoms
        assert "xmax" in self.geoms
        assert "ymin" in self.geoms
        assert "ymax" in self.geoms
