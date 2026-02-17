"""Contract compatibility test: verify decision-schema dependency."""

from decision_schema import __version__
from decision_schema.compat import is_compatible
from decision_schema.types import Proposal, FinalDecision, MismatchInfo, Action
from decision_schema.packet_v2 import PacketV2


def test_schema_version_import() -> None:
    """Verify schema version can be imported."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_schema_types_import() -> None:
    """Verify schema types can be imported."""
    assert Proposal is not None
    assert FinalDecision is not None
    assert MismatchInfo is not None
    assert Action is not None


def test_schema_packet_import() -> None:
    """Verify PacketV2 can be imported."""
    assert PacketV2 is not None


def test_schema_compatibility() -> None:
    """Verify schema version compatibility."""
    assert is_compatible(__version__, expected_major=0) is True


def test_backward_compat_aliases() -> None:
    """Verify backward compatibility aliases work."""
    # Action aliases
    assert Action.QUOTE == Action.ACT
    assert Action.FLATTEN == Action.EXIT
    assert Action.CANCEL_ALL == Action.CANCEL
