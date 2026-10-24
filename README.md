# Software Maturity Demonstrator

Reference project showing how a codebase reaches a high software maturity level
with Git and GitHub. It starts with a small C++ library and grows practice by
practice (see [docs/maturity-checklist.md](docs/maturity-checklist.md)).

## Layout

| Path                      | Purpose                                |
| ------------------------- | -------------------------------------- |
| `include/`, `src/`        | C++ library and demo executable        |
| `tests/`                  | GoogleTest unit tests                  |
| `conanfile.py`            | Dependencies (Conan 2)                 |
| `CMakeLists.txt`          | Build definition                       |
| `.pre-commit-config.yaml` | Hooks run by prek                      |
| `.github/CODEOWNERS`      | Required reviewers per path            |
| `.devcontainer/`          | Reproducible dev environment (Docker)  |
| `scripts/build.sh`        | Install, configure, build, test        |

## Usage

Open the folder in VS Code and choose **Reopen in Container**
(requires Docker and the Dev Containers extension). Then, in the container:

```sh
scripts/build.sh            # or: scripts/build.sh Debug
prek run --all-files
./build/Release/maturity_app
```

The git hook is installed automatically (`prek install`).
