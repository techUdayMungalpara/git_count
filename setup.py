from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="git-count",
    version="0.1.0",
    author="Uday Mungalpara",
    description="A command-line tool for visualizing git repository statistics with ASCII bars",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/techUdayMungalpara/git_count",
    packages=find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "git-count=git_count.git_count:main",
        ],
    },
)
