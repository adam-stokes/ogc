from __future__ import annotations

from ogc.db import connect
from ogc.models.layout import Layout
from ogc.models.tags import Tag

db = connect()
db.create_tables([Tag, Layout])

t = Tag(name="ogc", extra={"point": "1"})
t.save()

l = Layout(
    instance_size="e2-standard-4",
    name="ubuntu-ogc",
    provider="google",
    remote_path="/home/ubuntu/ogc",
    runs_on="ubuntu-2004-lts",
    scale=15,
    scripts="fixtures/ex_deploy_ubuntu",
    username="ubuntu",
    ssh_private_key="~/.ssh/id_rsa_libcloud",
    ssh_public_key="~/.ssh/id_rsa_libcloud.pub",
    ports=["22:22", "80:80", "443:443", "5601:5601"],
    labels=dict(
        division="engineering", org="obs", team="observability", project="perf"
    ),
)

l.save()

for t in Tag().select():
    print(t.extra["point"])

for _l in Layout().select():
    print(_l.name)
