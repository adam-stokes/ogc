""" Test dependency checker
"""
from ogc.dep import Dep, AptDep, SnapDep, PipDep

pkgs = [("apt:python3-pytest", AptDep),
        ("snap:conjure-up/latest/edge", SnapDep),
        ("pip:black>=1.2.3", PipDep)]

def test_load_dep_class():
    """ test_load_dep_class

    Make sure correct dep class loaded for specified package
    """
    for pkg, dep_type in pkgs:
        _dep = Dep.load(pkg)
        assert isinstance(_dep, dep_type)

def test_install_cmd():
    """ test_install_cmd

    Make sure we show correct install command, with and without sudo
    """
    for pkg, dep_type in pkgs:
        _dep = Dep.load(pkg)
        if isinstance(_dep, AptDep):
            _install_str = _dep.install_cmd()
            assert _install_str == "sudo apt-get install -qyf python3-pytest"
        if isinstance(_dep, SnapDep):
            _install_str = _dep.install_cmd()
            assert _install_str == "sudo snap install conjure-up --channel=latest/edge"
        if isinstance(_dep, PipDep):
            _install_str = _dep.install_cmd()
            assert _install_str == "pip install black>=1.2.3"

def test_package_name():
    """ test_package_name

    Make sure we have the correct package name
    """
    for pkg, dep_type in pkgs:
        _dep = Dep.load(pkg)
        if isinstance(_dep, AptDep):
            assert _dep.name == "python3-pytest"
        if isinstance(_dep, SnapDep):
            assert _dep.name == "conjure-up"
        if isinstance(_dep, PipDep):
            assert _dep.name == f"black"

    # Some other package testing with pip for regex
    pip_packages = ['pip:black==1.5.4',
                    "pip:awscli>=1.16,<2.0",
                    "pip:attrs==19.1.0",
                    "pip:boto3>=1.9,<2.0",
                    "pip:click>=7.0,<8.0",
                    "pip:jinja2>=2.10,<3.0",
                    "pip:juju-wait==2.7.0",
                    "pip:dict-deep==2.0.2",
                    "pip:juju>=0.11.7,<0.12.0",
                    "pip:kv>=0.3.0,<0.4.0",
                    "pip:launchpadlib==1.10.6",
                    "pip:melddict>=1.0,<2.0",
                    "pip:pyyaml-include>=1.1,<2.0"]

    pkg_package_names = ['black',
                         "awscli",
                         "attrs",
                         "boto3",
                         "click",
                         "jinja2",
                         "juju-wait",
                         "dict-deep",
                         "juju",
                         "kv",
                         "launchpadlib",
                         "melddict",
                         "pyyaml-include"]

    for pkg in pip_packages:
        _dep = Dep.load(pkg)
        assert set([_dep.name]).intersection(pkg_package_names)
