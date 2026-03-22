#!/usr/bin/env python3
"""Setup script for pdfnormal package."""

from setuptools import setup, find_packages

setup(
    name="pdfnormal",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    entry_points={
        "gui_scripts": [
            "pdfnormal=pdfnormal.main:main",
        ],
    },
)
