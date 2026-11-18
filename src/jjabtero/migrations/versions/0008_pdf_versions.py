"""논문마다 PDF 판을 여럿 두고, 읽던 위치와 주석을 판과 잇는다.

@doc: docs/design/Library.md#3-스키마-변경
@doc: docs/design/PdfVersions.md#3-데이터
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """스키마를 이 리비전으로 올린다. 있던 PDF는 지금 판이 되고, 위치와 주석은 그 판과 잇는다.

    @doc: docs/design/PdfVersions.md#3-데이터
    """
    op.create_table(
        "paper_pdfs_new",
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sha256", sa.String(), primary_key=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("drive_file_id", sa.String(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO paper_pdfs_new (paper_id, sha256, size, source, source_url, drive_file_id, page_count, added_at,"
        " selected_at) SELECT paper_id, sha256, size, source, source_url, drive_file_id, page_count, added_at, added_at"
        " FROM paper_pdfs"
    )
    op.create_table(
        "reading_positions_new",
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("pdf_sha256", sa.String(), primary_key=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("offset", sa.Float(), nullable=False),
        sa.Column("zoom", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    # PDF가 없는 논문의 위치는 쓸 곳이 없어 옮기지 않는다.
    op.execute(
        'INSERT INTO reading_positions_new (paper_id, pdf_sha256, page, "offset", zoom, updated_at)'
        ' SELECT r.paper_id, p.sha256, r.page, r."offset", r.zoom, r.updated_at'
        " FROM reading_positions r JOIN paper_pdfs p ON p.paper_id = r.paper_id"
    )
    op.drop_table("reading_positions")
    op.rename_table("reading_positions_new", "reading_positions")
    with op.batch_alter_table("annotations") as batch:
        batch.add_column(sa.Column("pdf_sha256", sa.String(), nullable=False, server_default=""))
    op.execute(
        "UPDATE annotations SET pdf_sha256 = COALESCE("
        "(SELECT sha256 FROM paper_pdfs WHERE paper_pdfs.paper_id = annotations.paper_id), '')"
    )
    op.drop_table("paper_pdfs")
    op.rename_table("paper_pdfs_new", "paper_pdfs")
    op.create_index("ix_annotations_paper_version", "annotations", ["paper_id", "pdf_sha256"])


def downgrade() -> None:
    """스키마를 이전 리비전으로 되돌린다. 논문마다 지금 판 하나만 남기고, 다른 판의 위치와 주석은 지운다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    op.drop_index("ix_annotations_paper_version", "annotations")
    current = (
        "SELECT sha256 FROM paper_pdfs c WHERE c.paper_id = {table}.paper_id"
        " ORDER BY c.selected_at DESC, c.added_at DESC, c.sha256 DESC LIMIT 1"
    )
    op.execute(f"DELETE FROM annotations WHERE pdf_sha256 IS NOT ({current.format(table='annotations')})")
    with op.batch_alter_table("annotations") as batch:
        batch.drop_column("pdf_sha256")
    op.create_table(
        "reading_positions_old",
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("offset", sa.Float(), nullable=False),
        sa.Column("zoom", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        'INSERT INTO reading_positions_old (paper_id, page, "offset", zoom, updated_at)'
        ' SELECT paper_id, page, "offset", zoom, updated_at FROM reading_positions'
        f" WHERE pdf_sha256 = ({current.format(table='reading_positions')})"
    )
    op.drop_table("reading_positions")
    op.rename_table("reading_positions_old", "reading_positions")
    op.create_table(
        "paper_pdfs_old",
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("drive_file_id", sa.String(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO paper_pdfs_old (paper_id, sha256, size, source, source_url, drive_file_id, page_count, added_at)"
        " SELECT paper_id, sha256, size, source, source_url, drive_file_id, page_count, added_at FROM paper_pdfs p"
        f" WHERE sha256 = ({current.format(table='p')})"
    )
    op.drop_table("paper_pdfs")
    op.rename_table("paper_pdfs_old", "paper_pdfs")
