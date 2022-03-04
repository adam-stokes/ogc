# pylint: disable=R0801
from pathlib import Path

from ogc.spec import SpecLoader

fixtures_dir = Path(__file__).parent / "fixtures"


def test_parse_layouts():
    """Test parsing of spec"""
    plan = SpecLoader.load([fixtures_dir / "spec.yml"])
    cluster_layout = plan.get_layout("cluster")
    assert len(cluster_layout) == 1
    assert cluster_layout[0].runs_on == "debian-latest"
    assert cluster_layout[0].provider == "aws"
