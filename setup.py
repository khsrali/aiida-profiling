from setuptools import setup, find_packages

setup(
    name="aiida_profiling",
    version="0.1",
    packages=find_packages(where="firecrest_"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[],  # List your dependencies here
)
