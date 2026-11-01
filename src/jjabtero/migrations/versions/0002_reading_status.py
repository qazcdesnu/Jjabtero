"""논문에 읽기 상태와 메모를 더한다.

@doc: docs/design/Library.md#3-스키마-변경
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """스키마를 이 리비전으로 올린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    with op.batch_alter_table("papers") as batch:
        batch.add_column(
            sa.Column("read_status", sa.String(), nullable=False, server_default="to-read")
        )
        batch.add_column(sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    """스키마를 이전 리비전으로 되돌린다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    with op.batch_alter_table("papers") as batch:
        batch.drop_column("note")
        batch.drop_column("read_status")
