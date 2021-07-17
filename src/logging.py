from rich.console import Console
from rich.theme import Theme

custom_theme = Theme(
    {"info": "green", "warning": "yellow", "error": "bold red"}
)
console = Console(theme=custom_theme)
