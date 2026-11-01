"""${message}

@doc: docs/design/Library.md#3-스키마-변경
"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """스키마를 이 리비전으로 올린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """스키마를 이전 리비전으로 되돌린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    ${downgrades if downgrades else "pass"}
