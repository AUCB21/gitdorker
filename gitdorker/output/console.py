from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from gitdorker.models import SearchResult

console = Console(stderr=True)


def print_result(result: SearchResult, report_path: Path) -> None:
    console.print(
        f"[green]✓[/green] [{result.search_type.value}] "
        f"[bold]{result.repo_full_name}[/bold] — "
        f"{result.file_path or result.url}  "
        f"[dim]→ {report_path.name}[/dim]"
    )


def print_summary(total: int, written: int, output_dir: Path, cycle: int | None = None) -> None:
    label = f"Summary — cycle {cycle}" if cycle is not None else "Summary"
    console.rule(f"[bold]{label}[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("Results found", str(total))
    table.add_row("Reports written", str(written))
    table.add_row("Output directory", str(output_dir.resolve()))
    console.print(table)


def print_error(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[blue]·[/blue] {msg}")
