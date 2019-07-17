import setuptools
from pathlib import Path

README = Path(__file__).parent.absolute() / 'readme.md'
README = README.read_text(encoding='utf8')

setuptools.setup(
    name="ogc",
    version="0.1.7",
    author="Adam Stokes",
    author_email="adam.stokes@ubuntu.com",
    description="ogc, a runner of things",
    long_description=README,
    long_description_content_type='text/markdown',
    url="https://github.com/battlemidget/ogc",
    packages=["ogc", "ogc.api", "ogc.commands", "ogc.models"],
    package_data={"": ["*"]},
    entry_points={"console_scripts": ["ogc = ogc.app:start"]},
    install_requires=[
        "awscli>=1.16,<2.0",
        "attrs==19.1.0",
        "boto3>=1.9,<2.0",
        "click>=7.0,<8.0",
        "jinja2>=2.10,<3.0",
        "juju-wait==2.7.0",
        "dict-deep==2.0.2",
        "flatten-dict==0.1.0",
        "juju>=0.11.7,<0.12.0",
        "kv>=0.3.0,<0.4.0",
        "launchpadlib==1.10.6",
        "melddict>=1.0,<2.0",
        "python-box>=3.4,<4.0",
        "pyyaml-include>=1.1,<2.0",
        "pyyaml==3.13",
        "requests>=2.22,<3.0",
        "semver>=2.8,<3.0",
        "sh>=1.12,<2.0",
        "staticjinja>=0.3.5,<0.4.0",
        "toml>=0.10.0,<0.11.0",
        "colorama==0.3.9",
    ],
)
