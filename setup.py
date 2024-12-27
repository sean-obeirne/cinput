from setuptools import setup, find_packages

setup(
    name="cinput",
    version="0.1.0",
    description="Input utilities for Python curses applications",
    author="Sean O'Beirne",
    author_email="sean.t.obeirne@gmail.com",
    url="https://github.com/sean-obeirne/cinput",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)

