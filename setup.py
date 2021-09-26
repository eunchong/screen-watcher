import imp
from os import path

from setuptools import setup

VERSION = imp.load_source("version", path.join(".", "src", "version.py"))
VERSION = VERSION.__version__


def read(fname):
    return open(path.join(path.dirname(__file__), fname)).read()


setup_kwargs = dict(
    name="screen-watcher",
    version=VERSION,
    description="watching screen processes",
    long_description_content_type="text/x-rst",
    long_description=read("README.rst"),
    author="eunchong",
    license="BSD",
    url="https://github.com/eunchong/screen-watcher",
    packages=["screen_watcher"],
    package_dir={"screen_watcher": "src"},
    install_requires=[
        "psutil>=5.8.0",
        "slacker>=0.12.0",
        "tabulate>=0.8.9",
        "SQLAlchemy>=1.4.25",
    ],
    entry_points={"console_scripts": ["screen-watcher = screen_watcher.main:main"]},
)

setup(**setup_kwargs)
