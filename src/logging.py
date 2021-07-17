from rich.console import Console
from rich.theme import Theme

custom_theme = Theme(
    {
        "debug": "magenta",
        "info": "green",
        "warning": "yellow",
        "error": "bold red",
    }
)
console = Console(theme=custom_theme, highlight=False)
