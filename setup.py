from pathlib import Path

import setuptools

README = Path(__file__).parent.absolute() / "readme.md"
README = README.read_text(encoding="utf8")

setuptools.setup(
    name="ogc",
    version="1.99.9",
    author="Adam Stokes",
    author_email="adam.stokes@ubuntu.com",
    description="ogc, a runner of things",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/battlemidget/ogc",
    packages=["ogc", "ogc.commands"],
    package_data={"": ["*"]},
    entry_points={
        "console_scripts": [
            "ogc = ogc.commands.base:start",
            "ogc-collect = ogc.commands.collect:start",
        ]
    },
    install_requires=[
        "click>=7.0,<8.0",
        "jinja2>=2.10,<3.0",
        "dict-deep==2.0.2",
        "loguru>=0.3.2,<1.99.9",
        "kv>=0.3,<0.4.0",
        "melddict>=1.0,<2.0",
        "pyyaml>=3.0,<6.0",
        "pyyaml-include>=1.1.1.1",
        "requests>=2.22,<3.0",
        "semver>=2.8,<3.0",
        "sh>=1.12,<2.0",
        "colorama==0.3.9",
        "python-dotenv==0.10.3",
        "tabulate==0.8.3",
        "boto3==1.9.229",
        "botocore==1.12.229",
    ],
    zip_safe=False,
)
