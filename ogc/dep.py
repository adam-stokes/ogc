""" Dependency checker module
"""
import click
import re


class Dep:
    pattern_match = None

    def __init__(self, package):
        self.package = package

    @classmethod
    def load(cls, package):
        if package.startswith("apt"):
            return AptDep(package)
        elif package.startswith("snap"):
            return SnapDep(package)
        elif package.startswith("pip"):
            return PipDep(package)

    @property
    def name(self):
        """ Return package name stripped of any dep type information
        """
        return self.parsed.group("name")

    @property
    def parsed(self):
        """ Parses the package name returning dictionary
        """
        _pattern = re.compile(self.pattern_match, re.VERBOSE)
        match = _pattern.match(self.package)
        return match

    def install_cmd(self):
        """ Show the install command for package
        """
        raise NotImplementedError


class AptDep(Dep):
    """ APT package dependency
    """

    pattern_match = r"""^(?P<type>apt):
                         (?P<name>[a-zA-Z0-9_.-]+)"""

    @property
    def name(self):
        return self.parsed.group("name")

    def install_cmd(self, sudo=True):
        cmd = [self.parsed.group("type")]
        if sudo:
            cmd.insert(0, "sudo")
        cmd_args = ["install", "-qyf", self.name]
        cmd = cmd + cmd_args
        return " ".join(cmd)


class SnapDep(Dep):
    """ Snap package dependency
    """

    pattern_match = r"""^(?P<type>snap):
                         (?P<name>[a-zA-Z0-9_.-]+)\/
                         (?P<track>[a-zA-Z0-9_.-]+)\/
                         (?P<channel>stable|candidate|beta|edge)
                         (?P<classic>:classic)?"""

    @property
    def name(self):
        return self.parsed.group("name")

    def install_cmd(self, sudo=True):
        cmd = [self.parsed.group("type")]
        if sudo:
            cmd.insert(0, "sudo")
        cmd_args = [
            "install",
            self.name,
            f"--channel={self.parsed.group('track')}/{self.parsed.group('channel')}",
        ]
        if self.parsed.group("classic"):
            cmd_args.append("--classic")
        cmd = cmd + cmd_args
        return " ".join(cmd)


class PipDep(Dep):
    """ Python PIP package dependency
    """

    pattern_match = r"""^(?P<type>pip):
                         (?P<name>[a-zA-Z0-9_.-]+)
                         (?P<version>[a-zA-Z0-9_.,<=>!-]+)?$"""

    @property
    def name(self):
        if "requirements.txt" in self.package:
            return self.package[4:]
        return self.parsed.group("name")

    def install_cmd(self, sudo=False):
        cmd = ["pip"]
        if sudo:
            cmd.insert(0, "sudo")
        if "requirements" in self.name:
            _name = f"-r{self.name}"
        else:
            version = self.parsed.group("version")
            if version:
                _name = f"{self.name}{version}"
            else:
                _name = self.name
        cmd_args = ["install", _name]
        cmd = cmd + cmd_args
        return " ".join(cmd)
