from setuptools import setup

setup(
    name="datasette_builder",
    version="0.1",
    packages=["datasette_builder"],
    install_requires=[
        "Click",
    ],
    entry_points="""
        [console_scripts]
        datasette_builder=datasette_builder.cli:cli
    """,
)
