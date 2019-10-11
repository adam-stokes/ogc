# OGC Specification

The spec file composed of configuration items in yaml format. There are
currently 2 top level properties that are accessed when the specification is
executed, the first is **meta** and the second is **plan**.


## Meta specification

The **meta** section provides more information on what the job does along with
certain properties that make generating specification documentation streamlined.

### Example

```yaml
meta:
  mkdocs:
    destination:
      - "releases/bugfix/index.md"
  name: Creating a bugfix release
  description: |
    Performs a Kubernetes bugfix release, which includes validation across the base
    deployment as well as variations including calico, tigera, vault, nvidia, and
    ceph.
  long-description: |
    ## Bugfix Release Process

    ### Cherry-pick fixes from master into stable branches

    ### Document release notes

    - Bugfixes
    - Enhancements
    - Known Limitations/Issues
```
### Properties

| Name | Description |
| -    | -           |
| name | The name of the spec |
| description | A short summary of what the spec is |
| long-description | A longer description of what the spec does, suppors **markdown** syntax. |

As seen in the above example there is a **mkdocs** property defined. This
configuration makes use of one of OGC's plugin called **ogc-plugins-spec-doc**.

When this plugin is executed it will go through and find all specification files
in the current directory and will convert them in a way that **mkdocs** can
generate documentation. This makes it easy to keep both the execution
environment and the documentation of what the specification does in a single
file.

The **destination** defined is where the resulting documentation will be
placed, for instance, this document will be copied over to
**docs/releases/bugfix/index.md** so that **mkdocs** will pick it up during
build.

To use this plugin:

```
pip install ogc-plugins-spec-doc
```

Configuring the plugin itself is done through an OGC Spec file of its own, for
example, we have a file called **maintainer-spec.yml**:

```yaml
meta:
  name: k8s ci maintainer spec
  description: |
    OGC Spec for generating documentation, running unittests, etc.

plan:
  - script:
      - specdoc:
          file-glob: jobs/**/*spec.yml
          top-level-dir: .
      - mkdocs build
```

Running this specifiation will collect all specifications matching the file glob
along with building the documentation through **mkdocs**.


## Plan specification

The **plan** section provides access to options that allow you model what your
execution environment will look like and how it will be run and validated.
