from setuptools import setup

setup(
    name="public_invest_api",
    version="1.0.0",
    description="Unofficial Public.com API",
    url="https://github.com/NelsonDane/public-invest-api",
    author="Nelson Dane",
    packages=["public_invest_api"],
    install_requires=["requests", "python-dotenv"],
)
