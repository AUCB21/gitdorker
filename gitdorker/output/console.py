from __future__ import annotations

from pathlib import Path
from typing import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from gitdorker.models import SearchResult

console = Console()


# ── Banner ────────────────────────────────────────────────────────────────────

def print_banner() -> None:
    banner = Text()
    banner.append("  git", style="bold yellow")
    banner.append("dorker", style="bold bright_yellow")
    banner.append("  v1.0", style="dim yellow")
    banner.append("  --  GitHub secret scanner  --  authorized use only\n", style="dim")
    console.print(banner)


# ── Live progress ─────────────────────────────────────────────────────────────

@contextmanager
def live_progress() -> Generator[Progress, None, None]:
    """Context manager yielding a rich Progress instance for dork scanning."""
    progress = Progress(
        SpinnerColumn(style="yellow"),
        TextColumn("[bold]{task.description}[/bold]"),
        TextColumn("[cyan]{task.fields[status]}[/cyan]"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    with progress:
        yield progress


# ── Per-result output ─────────────────────────────────────────────────────────

def print_result(result: SearchResult, report_path: Path) -> None:
    console.print(
        f"[green]✓[/green] [{result.search_type.value}] "
        f"[bold]{result.repo_full_name}[/bold] - "
        f"{result.file_path or result.url}  "
        f"[dim]→ {report_path.name}[/dim]"
    )


def print_summary(total: int, written: int, output_dir: Path, cycle: int | None = None) -> None:
    label = f"Summary - cycle {cycle}" if cycle is not None else "Summary"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", no_wrap=True)
    table.add_column()

    table.add_row("Candidates found", f"[yellow]{total}[/yellow]")
    table.add_row("Valid reports written", f"[green]{written}[/green]")
    table.add_row("Output directory", f"[dim]{output_dir.resolve()}[/dim]")
    if cycle is not None:
        table.add_row("Cycles completed", f"[blue]{cycle}[/blue]")

    console.print(Panel(table, title=f"[bold]{label}[/bold]", border_style="dim" if written == 0 else "green"))


def print_error(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[blue]·[/blue] {msg}")
