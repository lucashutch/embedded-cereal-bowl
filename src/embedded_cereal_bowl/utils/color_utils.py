from colorama import Back, Fore, Style


class colour_str:
    """A helper class to chain color/style codes for terminal output."""

    def __init__(self, s: str):
        self.s = s
        self.codes: list[str] = []

    def __str__(self) -> str:
        """Applies the stored codes when the object is converted to a string."""
        if not self.codes:
            return self.s

        prefix = "".join(self.codes)
        return f"{prefix}{self.s}{Style.RESET_ALL}"

    def _add_style(self, style_code: object) -> "colour_str":
        """Adds a style code and returns self to allow chaining."""
        self.codes.append(str(style_code))
        return self

    def red(self) -> "colour_str":
        return self._add_style(Fore.RED)

    def green(self) -> "colour_str":
        return self._add_style(Fore.GREEN)

    def yellow(self) -> "colour_str":
        return self._add_style(Fore.YELLOW)

    def blue(self) -> "colour_str":
        return self._add_style(Fore.BLUE)

    def black(self) -> "colour_str":
        return self._add_style(Fore.BLACK)

    def dim(self) -> "colour_str":
        return self._add_style(Style.DIM)

    def bright(self) -> "colour_str":
        return self._add_style(Style.BRIGHT)

    def back_red(self) -> "colour_str":
        return self._add_style(Back.RED)

    def back_green(self) -> "colour_str":
        return self._add_style(Back.GREEN)

    def back_blue(self) -> "colour_str":
        return self._add_style(Back.BLUE)

    def back_yellow(self) -> "colour_str":
        return self._add_style(Back.YELLOW)
