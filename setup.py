# -*- coding: utf-8 -*-
from setuptools import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
      name='honeybees',
      version='0.2',
      description='Honeybees is an agent-based modelling framework targeted at large-scale agent-based models.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='http://github.com/jensdebruijn/honeybees',
      author='Jens de Bruijn',
      author_email='j.a.debruijn@outlook.com',
      packages=[
            'honeybees',
            'honeybees.library',
            'honeybees.visualization',
            'honeybees.visualization.modules',
      ],
      package_data={
            'honeybees': [
                  'visualization/templates/*',
                  'visualization/templates/css/*',
                  'visualization/templates/js/*',
                  'visualization/templates/fonts/*',
                  'visualization/canvas/*.js'
            ],
            '': ['README.md']
      },
      include_package_data=True,
      zip_safe=False,
      install_requires=[
            "netcdf4",
            "pandas",
            "openpyxl",
            "geopandas",
            "numpy",
            "numba",
            "tbb",
            "tornado",
            "python-dateutil",
            "rasterio",
            "pyyaml",
            "matplotlib"
      ],
      extras_require = {
            'plotting':  ["cartopy"],
            'docs': ["sphinx", "sphinx_rtd_theme", "sphinx-autodoc-typehints", "sphinxcontrib-autoprogram"],
            'tests': ["matplotlib", "pytest", "pytest-plt", "pytest-benchmark"]
      }
)
