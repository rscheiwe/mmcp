import json
import subprocess
import sys
from pathlib import Path

import click
import toml
from packaging.version import parse

MIN_UV_VERSION = "0.4.10"


class PyProject:
    def __init__(self, path: Path):
        self.data = toml.load(path)

    @property
    def name(self) -> str:
        if "tool" in self.data and "poetry" in self.data["tool"]:
            return self.data["tool"]["poetry"]["name"]
        return self.data["project"]["name"]

    @property
    def first_binary(self) -> str | None:
        if "tool" in self.data and "poetry" in self.data["tool"]:
            scripts = self.data["tool"]["poetry"].get("scripts", {})
        else:
            scripts = self.data["project"].get("scripts", {})
        return next(iter(scripts.keys()), None)


def get_claude_config_path() -> Path | None:
    """Get the Claude config directory based on platform"""
    if sys.platform == "win32":
        path = Path(Path.home(), "AppData", "Roaming", "Claude")
    elif sys.platform == "darwin":
        path = Path(Path.home(), "Library", "Application Support", "Claude")
    else:
        return None

    if path.exists():
        return path
    return None


def has_claude_app() -> bool:
    return get_claude_config_path() is not None


def update_claude_config(project_name: str, project_path: Path) -> bool:
    """Add the project to the Claude config if possible"""
    config_dir = get_claude_config_path()
    if not config_dir:
        return False

    config_file = config_dir / "claude_desktop_config.json"
    if not config_file.exists():
        return False

    try:
        config = json.loads(config_file.read_text())
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        if project_name in config["mcpServers"]:
            click.echo(
                f"⚠️ Warning: {project_name} already exists in Claude.app configuration",
                err=True,
            )
            click.echo(f"Settings file location: {config_file}", err=True)
            return False

        config["mcpServers"][project_name] = {
            "command": "poetry",
            "args": ["run", project_name],
        }

        config_file.write_text(json.dumps(config, indent=2))
        click.echo(f"✅ Added {project_name} to Claude.app configuration")
        click.echo(f"Settings file location: {config_file}")
        return True
    except Exception:
        click.echo("❌ Failed to update Claude.app configuration", err=True)
        click.echo(f"Settings file location: {config_file}", err=True)
        return False


def get_package_directory(path: Path) -> Path:
    """Find the package directory under src/"""
    src_dir = next((path / "src").glob("*/__init__.py"), None)
    if src_dir is None:
        click.echo("❌ Error: Could not find __init__.py in src directory", err=True)
        sys.exit(1)
    return src_dir.parent


def copy_template(
    path: Path, 
    name: str, 
    description: str, 
    version: str = "0.1.0",
    with_examples: bool = False
) -> None:
    """Copy template files into src/<project_name>"""
    template_dir = Path(__file__).parent / "template"
    tools_dir = template_dir / "tools"
    services_dir = template_dir / "services"
    target_dir = get_package_directory(path)

    # Create required directories first
    (target_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (target_dir / "resources").mkdir(parents=True, exist_ok=True)
    (target_dir / "tools").mkdir(parents=True, exist_ok=True)
    (target_dir / "services").mkdir(parents=True, exist_ok=True)

    # Add debug output
    click.echo(f"Template directory: {template_dir}")
    click.echo(f"Template directory exists: {template_dir.exists()}")
    click.echo(f"Files in template directory: {list(template_dir.glob('*'))}")
    click.echo(f"Files in services directory: {list(services_dir.glob('*'))}")

    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(template_dir)))

    # Debug template loading
    click.echo(f"Available templates: {env.list_templates()}")

    # Main template files
    files = [
        ("server.py.jinja2", "server.py", target_dir),
        ("app.py.jinja2", "app.py", target_dir),
        ("README.md.jinja2", "README.md", path),
        ("Dockerfile.jinja2", "Dockerfile", path),
        ("docker-compose.yml.jinja2", "docker-compose.yml", path),
        (".env", ".env", path),
        # ("prompts/__init__.py.jinja2", "prompts/__init__.py", target_dir),
        # ("prompts/core.py.jinja2", "prompts/core.py", target_dir),
        # ("resources/__init__.py.jinja2", "resources/__init__.py", target_dir),
        # ("resources/core.py.jinja2", "resources/core.py", target_dir),
    ]

    # pyproject.toml
    pyproject = PyProject(path / "pyproject.toml")
    bin_name = pyproject.first_binary

    # template variables
    template_vars = {
        "binary_name": bin_name,
        "server_name": name,
        "server_version": version,
        "server_description": description,
        "server_directory": str(path.resolve()),
        "with_examples": with_examples,
    }

    try:
        # Copy main template files in the tools, prompts, and resources directories
        for template_file, output_file, output_dir in files:
            template = env.get_template(template_file)
            rendered = template.render(**template_vars)

            out_path = output_dir / output_file
            out_path.write_text(rendered)

        # Set up tools directory
        if tools_dir.exists():
            tools_target = target_dir / "tools"
            tools_target.mkdir(exist_ok=True)
            
            # Always copy core files
            core_files = ['__init__.py', 'base.py']
            for filename in core_files:
                tool_file = tools_dir / filename
                if tool_file.exists():
                    # Copy non-template files directly
                    import shutil
                    shutil.copy2(tool_file, tools_target / filename)

            if with_examples:
                # Copy additional example files when requested
                for tool_file in tools_dir.glob("*"):
                    if tool_file.is_file() and tool_file.name not in core_files:
                        if tool_file.suffix == '.jinja2':
                            # Handle template files
                            template = env.get_template(f"tools/{tool_file.name}")
                            rendered = template.render(**template_vars)
                            out_path = tools_target / tool_file.stem  # Remove .jinja2 extension
                            out_path.write_text(rendered)
                        else:
                            # Copy non-template files directly
                            import shutil
                            shutil.copy2(tool_file, tools_target / tool_file.name)

        # Set up services directory
        if services_dir.exists():
            services_target = target_dir / "services"
            services_target.mkdir(exist_ok=True)
            
            # Copy all service files
            for service_file in services_dir.glob("*"):
                if service_file.is_file():
                    if service_file.suffix == '.jinja2':
                        # Handle template files
                        template = env.get_template(f"services/{service_file.name}")
                        rendered = template.render(**template_vars)
                        out_path = services_target / service_file.stem  # Remove .jinja2 extension
                        out_path.write_text(rendered)
                    else:
                        # Copy non-template files directly
                        import shutil
                        shutil.copy2(service_file, services_target / service_file.name)

    except Exception as e:
        click.echo(f"❌ Error: Failed to template and write files: {e}", err=True)
        sys.exit(1)


def create_project(
    path: Path, name: str, description: str, version: str, use_claude: bool = True, with_examples: bool = False) -> None:
    """Create a new project using Poetry"""
    path.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize new Poetry project
        subprocess.run(
            ["poetry", "new", "--src", "--name", name, "."],
            cwd=path,
            check=True,
        )

        # Add mcp dependency using Poetry
        subprocess.run(
            ["poetry", "add", "mcp^1.1.2"],
            cwd=path,
            check=True,
        )

        # Update pyproject.toml with additional settings
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path) as f:
                pyproject = toml.load(f)
            
            # Ensure mcp dependency exists
            if "dependencies" not in pyproject["tool"]["poetry"]:
                pyproject["tool"]["poetry"]["dependencies"] = {}
            
            pyproject["tool"]["poetry"]["dependencies"]["mcp"] = "^1.1.2"
            
            with open(pyproject_path, "w") as f:
                toml.dump(pyproject, f)

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error: Failed to initialize Poetry project: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: Failed to update pyproject.toml: {e}", err=True)
        sys.exit(1)

    copy_template(path, name, description, version, with_examples)

    # Check if Claude.app is available
    if (
        use_claude
        and has_claude_app()
        and click.confirm(
            "\nClaude.app detected. Would you like to install the server into Claude.app now?",
            default=True,
        )
    ):
        update_claude_config(name, path)


def update_pyproject_settings(
    project_path: Path, version: str, description: str
) -> None:
    """Update project version and description in pyproject.toml"""
    import toml

    pyproject_path = project_path / "pyproject.toml"

    if not pyproject_path.exists():
        click.echo("❌ Error: pyproject.toml not found", err=True)
        sys.exit(1)

    try:
        pyproject = toml.load(pyproject_path)
        
        # Add debug output
        click.echo(f"Current pyproject.toml content: {pyproject}")

        if "tool" not in pyproject:
            pyproject["tool"] = {}
        if "poetry" not in pyproject["tool"]:
            pyproject["tool"]["poetry"] = {}

        if version is not None:
            pyproject["tool"]["poetry"]["version"] = version

        if description is not None:
            pyproject["tool"]["poetry"]["description"] = description

        pyproject_path.write_text(toml.dumps(pyproject))

    except Exception as e:
        click.echo(f"❌ Error updating pyproject.toml: {e}", err=True)
        sys.exit(1)


def check_package_name(name: str) -> bool:
    """Check if the package name is valid according to pyproject.toml spec"""
    if not name:
        click.echo("❌ Project name cannot be empty", err=True)
        return False
    if " " in name:
        click.echo("❌ Project name must not contain spaces", err=True)
        return False
    if not all(c.isascii() and (c.isalnum() or c in "_-.") for c in name):
        click.echo(
            "❌ Project name must consist of ASCII letters, digits, underscores, hyphens, and periods",
            err=True,
        )
        return False
    if name.startswith(("_", "-", ".")) or name.endswith(("_", "-", ".")):
        click.echo(
            "❌ Project name must not start or end with an underscore, hyphen, or period",
            err=True,
        )
        return False
    return True


def check_poetry_version() -> str | None:
    """Check if Poetry is installed"""
    try:
        result = subprocess.run(
            ["poetry", "--version"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def ensure_poetry_installed() -> None:
    """Ensure Poetry is installed"""
    if check_poetry_version() is None:
        click.echo("❌ Error: Poetry is required but not installed.", err=True)
        click.echo("To install, visit: https://python-poetry.org/docs/#installation", err=True)
        sys.exit(1)


def check_docker_available() -> bool:
    """Check if Docker is available"""
    try:
        subprocess.run(
            ["docker", "--version"], 
            capture_output=True, 
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
