import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gcbrickwork",
    version="0.0.1",
    author="Some Jake Guy",
    author_email="somejakeguy@gmail.com",
    description="A library of tools to read various GameCube files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SomeJakeGuy/gcbrickwork",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.12',
)