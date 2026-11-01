"""서재 테이블을 만든다.

@doc: docs/design/Library.md#3-스키마-변경
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """스키마를 이 리비전으로 올린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("venue", sa.String(), nullable=True),
        sa.Column("doi", sa.String(), nullable=True, unique=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_authors",
        sa.Column(
            "paper_id",
            sa.Integer(),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("authors.id"), nullable=False),
    )
    op.create_table(
        "paper_tags",
        sa.Column(
            "paper_id",
            sa.Integer(),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    """스키마를 이전 리비전으로 되돌린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.drop_table("paper_tags")
    op.drop_table("paper_authors")
    op.drop_table("papers")
    op.drop_table("tags")
    op.drop_table("authors")
