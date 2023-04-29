"""Setup File."""
from setuptools import setup

if __name__ == "__main__":
    with open("requirements.txt", encoding="utf-8") as file:
        required = file.read().splitlines()
    setup(install_requires=required)
