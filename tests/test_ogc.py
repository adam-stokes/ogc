import toml
from ogc.spec import SpecPlugin


def test_load_spec():
    spec_toml = toml.loads("""
[Info]
name = 'A test spec'
""")
    spec = SpecPlugin(spec_toml['Info'], spec_toml)
    assert "name" in spec.spec
