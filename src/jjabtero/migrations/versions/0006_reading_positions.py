"""읽던 위치 테이블을 만든다.

@doc: docs/design/Library.md#3-스키마-변경
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """스키마를 이 리비전으로 올린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.create_table(
        "reading_positions",
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("offset", sa.Float(), nullable=False),
        sa.Column("zoom", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """스키마를 이전 리비전으로 되돌린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.drop_table("reading_positions")
