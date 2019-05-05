import setuptools

with open("README.md", "r") as fh:
  long_description = fh.read()

setuptools.setup(
  name="protsupport",
  version="0.0.1",
  author="Michael Jendrusch",
  author_email="jendrusch@stud.uni-heidelberg.de",
  description="Pytorch extensions for working with proteins.",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/mjendrusch/protsupport/",
  packages=setuptools.find_packages(),
  classifiers=(
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
  ),
)
