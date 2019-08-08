import setuptools
from pathlib import Path

README = Path(__file__).parent.absolute() / "readme.md"
README = README.read_text(encoding="utf8")

setuptools.setup(
    name="ogc",
    version="0.3.14",
    author="Adam Stokes",
    author_email="adam.stokes@ubuntu.com",
    description="ogc, a runner of things",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/battlemidget/ogc",
    packages=["ogc", "ogc.commands"],
    package_data={"": ["*"]},
    entry_points={"console_scripts": ["ogc = ogc.app:start"]},
    install_requires=[
        "click>=7.0,<8.0",
        "jinja2>=2.10,<3.0",
        "dict-deep==2.0.2",
        "kv>=0.3,<0.4.0",
        "melddict>=1.0,<2.0",
        "pyyaml-include>=1.1,<2.0",
        "pyyaml<6.0.0",
        "requests>=2.22,<3.0",
        "semver>=2.8,<3.0",
        "sh>=1.12,<2.0",
        "colorama>=0.4.1",
        "pytest==5.0.1",
        "python-dotenv==0.10.3",
        "ogc-plugins-runner>=1.0.0,<2.0.0",
        "ogc-plugins-env>=1.0.0,<2.0.0",
    ],
    zip_safe=False
)
