import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gcbrickwork",
    packages=setuptools.find_packages(),
    version="3.0.4",
    license="MIT",
    author="Some Jake Guy",
    author_email="somejakeguy@gmail.com",
    description="A library of tools to read various GameCube files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SomeJakeGuy/gcbrickwork",
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords=["gcbrickwork", "gamecube", "prm", "jmp", "gc", "gc jmp", "gc prm", "param", "gc param"],
    install_requires=[],
    python_requires='>=3.12',
)
