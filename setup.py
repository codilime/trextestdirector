"""setup.py module for TRex test director package."""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="trex-test-scenario",
    version="0.0.1",
    author="Marcin Lembke",
    author_email="marcin.lembke@codilime.com",
    description="Simple tool for creating and running stateless TRex tests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/codilime/trextestdirector",
    packages=setuptools.find_packages(),
    install_requires=["PyYAML"],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.6",
)
