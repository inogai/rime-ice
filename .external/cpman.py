import os
import shutil
from pathlib import Path

import typer
import yaml
from pydantic import BaseModel, field_validator

CONFIG_ROOT = Path(__file__).parent.parent
EXT_ROOT = CONFIG_ROOT / ".external"
DEFINTION_DIR = EXT_ROOT / "definitions"
REPOSITORY_ROOT = EXT_ROOT / "repos"


class MoveInstruction(BaseModel):
    src: str
    dst: str

    def apply(self, package: str):
        repo_path = REPOSITORY_ROOT / package
        src_path = repo_path / self.src
        dst_path = CONFIG_ROOT / self.dst.replace(
            "$CONFIG_ROOT", CONFIG_ROOT.as_posix()
        )

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        _ = shutil.copy2(src_path, dst_path)

    def undo(self):
        dst_path = CONFIG_ROOT / self.dst.replace(
            "$CONFIG_ROOT", CONFIG_ROOT.as_posix()
        )
        os.remove(dst_path)


class PackageDefinition(BaseModel):
    name: str
    install: list[MoveInstruction]

    @field_validator("install", mode="before")
    def parse_install(cls, v) -> list[MoveInstruction]:
        if not isinstance(v, list):
            raise ValueError("install must be a list")

        instructions: list[MoveInstruction] = []

        for item in v:
            if isinstance(item, str):
                instructions.append(
                    MoveInstruction(src=item, dst="$CONFIG_ROOT/" + item)
                )
            else:
                raise ValueError("Unsupported install instruction format")

        return instructions

    def apply(self):
        for instruction in self.install:
            instruction.apply(package=self.name)

    def undo(self):
        for instruction in self.install:
            instruction.undo()


app = typer.Typer()


@app.command("list")
def list_all():
    """List installed packages."""

    available_packages = DEFINTION_DIR.glob("*.pkg.yaml")

    print("Available packages:")
    for pkg_file in available_packages:
        print(f"- {pkg_file.stem}")


@app.command()
def install(package: str):
    """Install a package."""
    typer.echo(f"Installing package: {package}")

    pkg_file = DEFINTION_DIR / f"{package}.pkg.yaml"
    if not pkg_file.exists():
        typer.echo(f"Package definition for '{package}' not found.")
        raise typer.Exit(code=1)

    pkg_obj = yaml.safe_load(pkg_file.read_text())
    pkg_def = PackageDefinition.model_validate(pkg_obj)

    for instruction in pkg_def.install:
        instruction.apply(package)


@app.command()
def uninstall(package: str):
    """Uninstall a package."""
    typer.echo(f"Uninstalling package: {package}")

    pkg_file = DEFINTION_DIR / f"{package}.pkg.yaml"
    if not pkg_file.exists():
        typer.echo(f"Package definition for '{package}' not found.")
        raise typer.Exit(code=1)

    pkg_obj = yaml.safe_load(pkg_file.read_text())
    pkg_def = PackageDefinition.model_validate(pkg_obj)

    for instruction in pkg_def.install:
        instruction.undo()


if __name__ == "__main__":
    app()
