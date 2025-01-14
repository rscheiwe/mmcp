import click
from . import create_project, update_pyproject_settings, check_package_name, ensure_poetry_installed, check_docker_available
from pathlib import Path
from packaging.version import parse
import subprocess
import toml
import os
from .utils import format_tool_name


@click.group()
def main():
    """MMCP CLI - Tools for working with Model Context Protocol servers"""
    pass

@main.command()
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    help="Directory to create project in",
)
@click.option(
    "--name",
    type=str,
    help="Project name",
)
@click.option(
    "--version",
    type=str,
    help="Server version",
)
@click.option(
    "--description",
    type=str,
    help="Project description",
)
@click.option(
    "--claudeapp/--no-claudeapp",
    default=False,
    help="Enable/disable Claude.app integration (disabled by default)",
)
@click.option(
    "--with-examples/--no-examples",
    default=False,
    help="Include example tools and utilities (disabled by default)",
)
def create_mmcp(
    path: Path | None,
    name: str | None,
    version: str | None,
    description: str | None,
    claudeapp: bool,
    with_examples: bool,
) -> int:
    """Create a new MCP server project"""
    ensure_poetry_installed()

    # Check for optional Docker dependency
    if not check_docker_available():
        click.echo("\n⚠️ Warning: Docker is not available. Some features may be limited.", err=True)
        click.echo("To install Docker, visit: https://docs.docker.com/get-docker/")
        
        if click.confirm("\nWould you like to abort the flow to install Docker first?", default=False):
            click.echo("\nAborting. Please install Docker and try again.")
            return 1
            
        click.echo("\nContinuing without Docker...\n")

    click.echo("Creating a new mMCP server project using Poetry.")
    click.echo("This will set up a Python project with mMCP dependency.")

    if not claudeapp:
        click.echo("Note: Claude.app integration is disabled by default. Use --claudeapp to enable.")

    click.echo("\nLet's begin!\n")

    name = click.prompt("Project name (required)", type=str) if name is None else name

    if name is None:
        click.echo("❌ Error: Project name cannot be empty", err=True)
        return 1

    if not check_package_name(name):
        return 1

    description = (
        click.prompt("Project description", type=str, default="An mMCP server project.")
        if description is None
        else description
    )

    assert isinstance(description, str)

    # Validate version if not supplied on command line
    if version is None:
        version = click.prompt("Project version", default="0.1.0", type=str)
        assert isinstance(version, str)
        try:
            parse(version)  # Validate semver format
        except Exception:
            click.echo(
                "❌ Error: Version must be a valid semantic version (e.g. 1.0.0)",
                err=True,
            )
            return 1

    project_path = (Path.cwd() / name) if path is None else path

    # Ask the user if the path is correct if not specified on command line
    if path is None:
        click.echo(f"Project will be created at: {project_path}")
        if not click.confirm("Is this path/location correct?", default=True):
            project_path = Path(
                click.prompt("Enter the correct path", type=click.Path(path_type=Path))
            )

    if project_path is None:
        click.echo("❌ Error: Invalid path. Project creation aborted.", err=True)
        return 1

    project_path = project_path.resolve()

    create_project(project_path, name, description, version, claudeapp, with_examples)
    update_pyproject_settings(project_path, version, description)

    click.echo("\n✅ Project created successfully!")
    click.echo(f"Project directory: {project_path}")
    click.echo("ℹ️ To install dependencies run:")
    click.echo(f"   >> cd {project_path}")
    click.echo("   >> poetry install")
    click.echo("\nℹ️ To run the server, you can use either:")
    click.echo(f"   >> poetry run python -m {name}.server")
    click.echo("   or")
    click.echo("   >> mmcp run server")
    click.echo("\nThe mmcp command supports additional options:")
    click.echo("   >> mmcp run server --port 3000 --host 0.0.0.0 --reload")
    click.echo("\nℹ️ To run via Docker, use:")
    click.echo("   >> docker compose up -d --build")

    return 0


@main.group()
def add():
    """Add components to your MCP server"""
    pass

@add.command()
@click.argument('name', type=str, required=False)
@click.option(
    '--description',
    '-d',
    type=str,
    help='Description of the tool',
    default="A custom MCP tool"
)
@click.option(
    '--path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help='Path to the MCP project (defaults to current directory)'
)
def tool(name: str | None, description: str, path: Path):
    """Add a new tool to an existing MCP server project"""
    if name is None:
        name = click.prompt("Tool name (required)", type=str)
    
    # Format the tool name
    name = format_tool_name(name)
    
    try:
        # Verify this is an MCP project directory
        if not (path / "pyproject.toml").exists():
            click.echo("❌ Error: No pyproject.toml found. Are you in an MCP project directory?", err=True)
            return 1

        # Create tools directory if it doesn't exist
        tools_dir = path / "src" / path.name / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        # Create the tool file
        tool_file = tools_dir / f"{name}.py"
        if tool_file.exists():
            if not click.confirm(f"Tool {name} already exists. Overwrite?", default=False):
                click.echo("Aborted.", err=True)
                return 1

        # Write the tool template
        tool_content = f'''from typing import Dict, Any
from mcp.types import Tool, TextContent
from .base import BaseTool
from pydantic import BaseModel, Field


class {name}Input(BaseModel):
    # Add your input parameters here
    parameter: str = Field(..., description="Description of the parameter")


class {name}Tool(BaseTool):
    name = "{name}"
    description = "{description}"
    
    @staticmethod
    async def execute(arguments: {name}Input) -> list[TextContent]:
        # Add your tool implementation here
        parameter = arguments.parameter

        # TODO: Add your tool logic here
        # See documentation for more details: https://mcp.readthedocs.io/en/latest/
        
        return [TextContent(
            type="text",
            text=f"Hello from {name}! Parameter: {{parameter}}"  # Note the double {{}} to escape
        )]

    @staticmethod
    def get_schema() -> Tool:
        return Tool(
            name={name}Tool.name,
            description={name}Tool.description,
            inputSchema={name}Input.model_json_schema()
        )
'''
        tool_file.write_text(tool_content)

        # Update __init__.py to include the new tool
        init_file = tools_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("from . import core\n\n__all__ = ['core']\n")

        init_content = init_file.read_text()
        if f"from . import {name}" not in init_content:
            lines = init_content.splitlines()
            lines.insert(1, f"from . import {name}")
            for i, line in enumerate(lines):
                if "__all__" in line:
                    lines[i] = line.replace("]", f", '{name}']")
                    break
            init_file.write_text("\n".join(lines) + "\n")

        # Update server.py to register the new tool
        server_file = path / "src" / path.name / "server.py"
        if server_file.exists():
            content = server_file.read_text()
            lines = content.splitlines()
            
            for i, line in enumerate(lines):
                if "def post_init():" in line:
                    j = i + 1
                    while j < len(lines) and (lines[j].strip().startswith('#') or not lines[j].strip()):
                        j += 1
                    lines.insert(j, f"    from .tools.{name} import {name}Tool")
                    lines.insert(j + 1, f"    tool_service.register_tool({name}Tool())")
                    break
            
            server_file.write_text("\n".join(lines))
            click.echo(f"✅ Tool registered in server.py")
            click.echo(f"✅ Please confirm the tool is registered.")
            
        else:
            click.echo("⚠️ Warning: Could not find server.py to register the tool.")
            click.echo(f"Please manually add the following to your post_init() function:")
            click.echo(f"    from .tools.{name} import {name}Tool")
            click.echo(f"    tool_service.register_tool({name}Tool())")

        click.echo(f"✅ Successfully created tool: {name}")
        click.echo(f"Tool file created at: {tool_file}")
        click.echo("\nTo use this tool, implement your logic in the function body and update the parameters as needed.")

    except Exception as e:
        click.echo(f"❌ Error creating tool: {e}", err=True)
        return 1

    return 0

@main.group()
def run():
    """Run MCP server components"""
    pass

@run.command()
@click.option(
    '--path',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help='Path to the MCP project (defaults to current directory)'
)
@click.option(
    '--port',
    type=int,
    default=8080,
    help='Port to run the server on'
)
@click.option(
    '--host',
    type=str,
    default="127.0.0.1",
    help='Host to bind to'
)
@click.option(
    '--reload',
    is_flag=True,
    default=False,
    help='Enable auto-reload for development'
)
def server(path: Path, port: int, host: str, reload: bool):
    """Run the MCP server"""
    try:
        pyproject_path = path / "pyproject.toml"
        if not pyproject_path.exists():
            click.echo("❌ Error: No pyproject.toml found. Are you in an MCP project directory?", err=True)
            return 1

        with open(pyproject_path) as f:
            pyproject = toml.load(f)
            project_name = pyproject["tool"]["poetry"]["name"]

        click.echo(f"Starting {project_name} server on {host}:{port}...")
        
        cmd = ["poetry", "run", "python", "-m", f"{project_name}.server"]
        if reload:
            cmd.append("--reload")
        
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = host
        
        subprocess.run(
            cmd,
            cwd=path,
            env=env,
            check=True
        )

    except Exception as e:
        click.echo(f"❌ Error starting server: {e}", err=True)
        return 1

    return 0
