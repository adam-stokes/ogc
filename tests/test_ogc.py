# pylint: disable=R0801
from __future__ import annotations

import os
from pathlib import Path

from ogc.spec import SpecLoader

fixtures_dir = Path(__file__).parent / "fixtures"


def test_parse_layouts() -> None:
    """Test parsing of spec"""
    plan = SpecLoader.load([fixtures_dir / "spec.toml"])
    cluster_layout = plan.get_layout("elastic-agent-ubuntu")
    assert len(cluster_layout) == 1
    assert cluster_layout[0].runs_on == "ubuntu-2004-lts"
    assert cluster_layout[0].provider == "google"


def test_parse_spec_interpolated() -> None:
    """Test that a spec with interpolated values can be referenced"""
    plan = SpecLoader.load([fixtures_dir / "spec-interpolated.toml"])
    cluster_layout = plan.get_layout("elastic-agent-ubuntu")
    cluster = cluster_layout[0]
    assert cluster.artifacts == "/home/ubuntu/ogc/output/*.xml"


def test_parse_spec_interpolated_env() -> None:
    """Test that a spec with environment vars can be referenced"""
    os.environ["INSTANCE_SIZE"] = "e2-standard-8"
    plan = SpecLoader.load([fixtures_dir / "spec-interpolated.toml"])
    cluster_layout = plan.get_layout("elastic-agent-ubuntu")
    cluster = cluster_layout[0]
    assert cluster.instance_size == "e2-standard-8"


def test_parse_spec_interpolated_env_empty() -> None:
    """Test that a spec with environment vars can use the default if no env is set"""
    del os.environ["INSTANCE_SIZE"]
    plan = SpecLoader.load([fixtures_dir / "spec-interpolated.toml"])
    cluster_layout = plan.get_layout("elastic-agent-ubuntu")
    cluster = cluster_layout[0]
    assert cluster.instance_size == "e2-standard-4"
