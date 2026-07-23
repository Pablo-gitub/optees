from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.contracts.json_value import JsonValue, require_json_value


@dataclass(frozen=True)
class ArtifactSource:
    """Immutable solver input/output pair retained for headless rendering."""

    capability_id: str
    problem: dict[str, JsonValue]
    envelope: ExecutionEnvelope

    def __post_init__(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("artifact source capability_id must not be empty")
        if self.capability_id != self.envelope.capability_id:
            raise ValueError("artifact source capability must match its envelope")
        require_json_value(self.problem, path="$.artifact_source.problem")


@dataclass(frozen=True)
class ArtifactRenderOptions:
    """Normalized options shared by every headless renderer."""

    locale: str = "en"
    theme: str = "light"
    width: int = 1280
    height: int = 720
    font_family: str = "DejaVu Sans"
    extra: dict[str, JsonValue] | None = None

    def __post_init__(self) -> None:
        if self.locale not in {"en", "it"}:
            raise ValueError("artifact locale must be 'en' or 'it'")
        if self.theme not in {"light", "dark"}:
            raise ValueError("artifact theme must be 'light' or 'dark'")
        _require_dimension(self.width, "width", minimum=320)
        _require_dimension(self.height, "height", minimum=240)
        if self.width * self.height > 16_000_000:
            raise ValueError("artifact raster area must not exceed 16 megapixels")
        if self.font_family != "DejaVu Sans":
            raise ValueError("artifact font_family must use the bundled deterministic font")
        if self.extra is not None:
            require_json_value(self.extra, path="$.artifact_render_options.extra")

    def to_dict(self) -> dict[str, JsonValue]:
        payload = require_json_value(
            {
                "locale": self.locale,
                "theme": self.theme,
                "width": self.width,
                "height": self.height,
                "font_family": self.font_family,
                "extra": self.extra or {},
            },
            path="$.artifact_render_options",
        )
        assert isinstance(payload, dict)
        return payload


@dataclass(frozen=True)
class ArtifactRenderContext:
    capability_id: str
    artifact_type: str
    format: ArtifactFormat
    problem: dict[str, JsonValue]
    envelope: ExecutionEnvelope
    options: ArtifactRenderOptions

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or not self.artifact_type.strip():
            raise ValueError("render context identifiers must not be empty")
        if self.capability_id != self.envelope.capability_id:
            raise ValueError("render context capability must match the execution envelope")
        require_json_value(self.problem, path="$.artifact_render_context.problem")


@dataclass(frozen=True)
class RenderedArtifact:
    media_type: str
    content: bytes

    def __post_init__(self) -> None:
        if not self.media_type.strip():
            raise ValueError("rendered artifact media_type must not be empty")
        if not self.content:
            raise ValueError("rendered artifact content must not be empty")


def _require_dimension(value: int, name: str, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"artifact {name} must be an integer")
    if value < minimum or value > 4096:
        raise ValueError(f"artifact {name} must be between {minimum} and 4096")
