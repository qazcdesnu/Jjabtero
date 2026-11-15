"""PDF 주석(하이라이트, 영역 메모) 테이블을 만든다.

@doc: docs/design/Library.md#3-스키마-변경
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """스키마를 이 리비전으로 올린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("rects", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_annotations_paper_id", "annotations", ["paper_id"])


def downgrade() -> None:
    """스키마를 이전 리비전으로 되돌린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.drop_index("ix_annotations_paper_id", "annotations")
    op.drop_table("annotations")
