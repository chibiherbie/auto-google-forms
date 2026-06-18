from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    max_attempts: int = 1
    delay_seconds: float = 0.0
    retry_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    continue_on_error: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must not be negative")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must not be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
