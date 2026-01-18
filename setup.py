from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="git-count",
    version="0.2.0",
    author="Uday Mungalpara",
    author_email="your.email@example.com",
    description="A Git commit activity visualization tool with detailed repository insights",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/techUdayMungalpara/git_count",
    project_urls={
        "Bug Reports": "https://github.com/techUdayMungalpara/git_count/issues",
        "Source": "https://github.com/techUdayMungalpara/git_count",
        "Documentation": "https://github.com/techUdayMungalpara/git_count#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Utilities",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    keywords="git commits visualization analytics statistics",
    entry_points={
        "console_scripts": [
            "git-count=git_count.git_count:main",
        ],
    },
)
