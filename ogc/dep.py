""" Dependency checker module
"""
import click
import re


class Dep:
    def __init__(self, package):
        self.package = package

    @classmethod
    def load(cls, package):
        if package.startswith('apt'):
            return AptDep(package)
        elif package.startswith('snap'):
            return SnapDep(package)
        elif package.startswith('pip'):
            return PipDep(package)

    def __str__(self):
        return self.package.strip()

    @property
    def name(self):
        """ Return package name stripped of any dep type information
        """
        return self.__str__()

    def install_cmd(self):
        """ Show the install command for package
        """
        raise NotImplementedError


class AptDep(Dep):
    """ APT package dependency
    """
    @property
    def name(self):
        return self.package[4:]

    def install_cmd(self, sudo=True):
        cmd = ['apt-get']
        if sudo:
            cmd.insert(0, 'sudo')
        cmd_args = ["install", "-qyf", self.package[4:]]
        cmd = cmd + cmd_args
        return " ".join(cmd)


class SnapDep(Dep):
    """ Snap package dependency
    """
    @property
    def name(self):
        return self.package[5:].split('/')[0]

    def install_cmd(self, sudo=True):
        pkg_line = self.package[5:]
        cmd = ['snap']
        if sudo:
            cmd.insert(0, 'sudo')
        _package = pkg_line.split('/')
        if len(_package) != 3:
            raise DepError("Must have a <packagename>/<track>/<channel> set.")
        name, track, channel = _package
        cmd_args = ["install", name, f"--channel={track}/{channel}"]
        cmd = cmd + cmd_args
        return " ".join(cmd)

class PipDep(Dep):
    """ Python PIP package dependency
    """
    @property
    def name(self):
        pattern = re.compile("^(\w+-?\w+)")
        match = pattern.match(self.package[4:])
        return match.group(0)

    def install_cmd(self, sudo=False):
        cmd = ['pip']
        if sudo:
            cmd.insert(0, 'sudo')
        cmd_args = ["install", self.package[4:]]
        cmd = cmd + cmd_args
        return " ".join(cmd)
