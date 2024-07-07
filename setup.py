from pathlib import Path

from setuptools import setup, find_packages

here = Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="bgp-anomaly-detection",
    version="0.0.1",
    description="A sample Python project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gvlk/bgp-anomaly-detection",
    author="Guilherme Azambuja",
    author_email="guilhermevazambuja@gmail.com",
    package_dir={"": "bgp_anomaly_detection"},
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["mrtparse", "matplotlib", "pandas"],
    extras_require=["faker"],
    entry_points={
        "console_scripts": [
            "sample=sample:main"
        ],
    },
)
