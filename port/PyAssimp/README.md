PyAssimp Readme
===============

A simple Python wrapper for Assimp using `ctypes` to access the library.
Requires Python >= 2.6.

Python 3 support is mostly here, but not well tested.

Note that pyassimp is not complete. Many ASSIMP features are missing.

USAGE
-----

### Complete example: 3D viewer

`pyassimp` comes with a simple 3D viewer that shows how to load and display a 3D
model using a shader-based OpenGL pipeline.

![Screenshot](3d_viewer_screenshot.png)

To use it, from within `/port/PyAssimp`:

```console
$ cd scripts
$ python ./3D-viewer <path to your model>
```

You can use this code as starting point in your applications.

### Writing your own code

To get started with `pyassimp`, examine the simpler `sample.py` script in `scripts/`,
which illustrates the basic usage. All Assimp data structures are wrapped using
`ctypes`. All the data+length fields in Assimp's data structures (such as
`aiMesh::mNumVertices`, `aiMesh::mVertices`) are replaced by simple python
lists, so you can call `len()` on them to get their respective size and access
members using `[]`.

For example, to load a file named `hello.3ds` and print the first
vertex of the first mesh, you would do (proper error handling
substituted by assertions ...):

```python

from pyassimp import load
with load('hello.3ds') as scene:

  assert len(scene.meshes)
  mesh = scene.meshes[0]

  assert len(mesh.vertices)
  print(mesh.vertices[0])

```

Another example to list the 'top nodes' in a
scene:

```python

from pyassimp import load
with load('hello.3ds') as scene:

  for c in scene.rootnode.children:
      print(str(c))

```

INSTALL
-------

Install `pyassimp` by running:

```console
$ pip install .
```

Or install directly from the git repository:

```console
$ pip install "pyassimp @ git+https://github.com/assimp/assimp#subdirectory=port/PyAssimp"
```

### Precompiled binaries (recommended)

PyAssimp requires the assimp native library (`DLL` on Windows,
`.so` on Linux, `.dylib` on macOS). The easiest way to get it is
to let pyassimp download a precompiled binary from the
[official GitHub releases](https://github.com/assimp/assimp/releases):

```console
$ pyassimp-download-libs            # download for the latest release
$ pyassimp-download-libs v6.0.4     # download for a specific release tag
```

You can also run the downloader as a module:

```console
$ python -m pyassimp.library_downloader
```

Alternatively, the library will be **downloaded automatically** on
first import if no local copy is found. Set the environment variable
`PYASSIMP_NO_AUTO_DOWNLOAD=1` to disable this behaviour.

To select a specific release tag for auto-download, set
`PYASSIMP_RELEASE_TAG` (e.g. `PYASSIMP_RELEASE_TAG=v6.0.4`).

### Manual installation

If you prefer to compile assimp yourself, make sure the shared library
is placed in one of the default search directories:
  - the current directory
  - on Linux additionally: `/usr/lib`, `/usr/local/lib`,
    `/usr/lib/x86_64-linux-gnu`

To build that library, refer to the Assimp master `INSTALL`
instructions. To look in more places, edit `./pyassimp/helper.py`.
There's an `additional_dirs` list waiting for your entries.
