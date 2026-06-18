class ConfigError(ValueError):
    """Raised when a configuration cannot be decoded or validated."""


class ConfigDecodeError(ConfigError):
    """Raised when JSON does not match the expected structure."""


class ConfigValidationError(ConfigError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


class FormImportError(ValueError):
    """Raised when a form cannot be downloaded or parsed."""


class PlanBuildError(ValueError):
    """Raised when individual responses cannot be built from a valid plan."""
