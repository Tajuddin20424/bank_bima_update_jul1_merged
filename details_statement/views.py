from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape


DETAILS_STATEMENT_HEADERS = [
    "SL", "Invoice No", "Date", "Main Head", "Product", "Transaction With",
    "Net", "Discount", "Receive", "Payment",
]


def build_statement_filters(main_head="", start_date="", end_date=""):
    where = ["1 = 1"]
    params = []
    if main_head:
        where.append("d.tran_type = %s")
        params.append(main_head)
    if start_date:
        where.append("d.tran_date >= %s")
        params.append(start_date)
    if end_date:
        where.append("d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(end_date)
    return where, params


def _statement_sql(where_sql):
    return f"""
        SELECT
            d.id, COALESCE(d.invoice_ref, d.tran_id, '') AS invoice_no,
            d.tran_date,
            COALESCE(mh.type_name, CAST(d.tran_type AS CHAR)) AS main_head_name,
            COALESCE(th.tran_head_name, '') AS tran_head_name,
            COALESCE(tw.tran_with_name, CAST(d.tran_type_with AS CHAR), '') AS tran_with_name,
            CASE
                WHEN LOWER(COALESCE(d.payment_mode, '')) = 'receive' THEN COALESCE(d.receive, 0)
                WHEN LOWER(COALESCE(d.payment_mode, '')) = 'payment' THEN 0
                ELSE COALESCE(d.receive, 0)
            END AS receive,
            CASE
                WHEN LOWER(COALESCE(d.payment_mode, '')) = 'payment' THEN COALESCE(d.payment, 0)
                WHEN LOWER(COALESCE(d.payment_mode, '')) = 'receive' THEN 0
                ELSE COALESCE(d.payment, 0)
            END AS payment,
            COALESCE(d.discount, 0) AS discount,
            COALESCE(d.tot_amount, d.amount, 0) AS net_amount,
            COALESCE(d.due, 0) AS due
        FROM transaction__details d
        LEFT JOIN transaction__main__heads mh ON mh.id = d.tran_type
        LEFT JOIN transaction__heads th ON th.id = d.tran_head_id
        LEFT JOIN transaction__withs tw ON tw.id = d.tran_type_with
        WHERE {where_sql}
        ORDER BY d.tran_type ASC, d.tran_date ASC, d.id ASC
    """


def _balance_sql(where_sql):
    """Return receive minus payment for the filtered detail rows."""
    receive_sql = """
        CASE
            WHEN LOWER(COALESCE(d.payment_mode, '')) = 'receive' THEN COALESCE(d.receive, 0)
            WHEN LOWER(COALESCE(d.payment_mode, '')) = 'payment' THEN 0
            ELSE COALESCE(d.receive, 0)
        END
    """
    payment_sql = """
        CASE
            WHEN LOWER(COALESCE(d.payment_mode, '')) = 'payment' THEN COALESCE(d.payment, 0)
            WHEN LOWER(COALESCE(d.payment_mode, '')) = 'receive' THEN 0
            ELSE COALESCE(d.payment, 0)
        END
    """
    return f"""
        SELECT COALESCE(SUM({receive_sql}), 0) - COALESCE(SUM({payment_sql}), 0)
        FROM transaction__details d
        WHERE {where_sql}
    """


def _rows_and_filters(request):
    today = timezone.localdate().isoformat()
    main_head = (request.GET.get("main_head") or "").strip()
    start_date = (request.GET.get("start_date") or today).strip()
    end_date = (request.GET.get("end_date") or today).strip()
    where, params = build_statement_filters(main_head, start_date, end_date)
    opening_where = ["1 = 1"]
    opening_params = []
    if main_head:
        opening_where.append("d.tran_type = %s")
        opening_params.append(main_head)
    opening_where.append("d.tran_date < %s")
    opening_params.append(start_date)
    closing_where = ["1 = 1", "d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)"]
    closing_params = [end_date]
    if main_head:
        closing_where.insert(1, "d.tran_type = %s")
        closing_params.insert(0, main_head)
    with connection.cursor() as cursor:
        cursor.execute(_statement_sql(" AND ".join(where)), params)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.execute(_balance_sql(" AND ".join(opening_where)), opening_params)
        opening_balance = float(cursor.fetchone()[0] or 0)
        cursor.execute(_balance_sql(" AND ".join(closing_where)), closing_params)
        closing_balance = float(cursor.fetchone()[0] or 0)
        cursor.execute("""
            SELECT id, type_name
            FROM transaction__main__heads
            ORDER BY type_name ASC
        """)
        main_heads = cursor.fetchall()
    return (
        rows, main_heads, main_head, start_date, end_date,
        opening_balance, closing_balance,
    )


def details_statement(request):
    rows, main_heads, main_head, start_date, end_date, opening_balance, closing_balance = _rows_and_filters(request)
    return render(request, "details_statement/list.html", {
        "rows": rows,
        "main_heads": main_heads,
        "selected_main_head": main_head,
        "start_date": start_date,
        "end_date": end_date,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
    })


def _report_cell(value, style):
    return Paragraph(escape(str(value if value is not None else "")), style)


def details_statement_pdf(request):
    rows, _, main_head, start_date, end_date, opening_balance, closing_balance = _rows_and_filters(request)
    selected_name = "All Main Heads"
    if main_head:
        with connection.cursor() as cursor:
            cursor.execute("SELECT type_name FROM transaction__main__heads WHERE id = %s", [main_head])
            selected = cursor.fetchone()
        selected_name = selected[0] if selected else main_head

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "DetailsStatementCell", parent=styles["Normal"], fontName="Helvetica",
        fontSize=6.2, leading=7.2, spaceBefore=0, spaceAfter=0,
    )
    header_style = ParagraphStyle(
        "DetailsStatementHeader", parent=cell_style, fontName="Helvetica-Bold",
        alignment=1,
    )
    table_data = [[_report_cell(value, header_style) for value in DETAILS_STATEMENT_HEADERS]]
    numeric_keys = {"receive", "payment", "discount", "net_amount"}
    keys = ["invoice_no", "tran_date", "main_head_name", "tran_head_name", "tran_with_name", "net_amount", "discount", "receive", "payment"]
    for index, row in enumerate(rows, 1):
        values = [index]
        for key in keys:
            value = row.get(key, "")
            if key in numeric_keys:
                value = f"{float(value or 0):.2f}"
            values.append(value)
        table_data.append([_report_cell(value, cell_style) for value in values])
    if not rows:
        table_data.append([_report_cell("No detail transactions found", cell_style)] + [""] * (len(DETAILS_STATEMENT_HEADERS) - 1))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="details_statement.pdf"'
    document = SimpleDocTemplate(
        response, pagesize=landscape(A4), rightMargin=10 * mm, leftMargin=10 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    title_style = ParagraphStyle(
        "DetailsStatementTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=14, leading=17, alignment=1, spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "DetailsStatementMeta", parent=styles["Normal"], fontSize=8, leading=10,
        alignment=1, spaceAfter=8,
    )
    elements = [
        Paragraph("Details Statement", title_style),
        Paragraph(
            f"Main Head: <b>{escape(str(selected_name))}</b> &nbsp;&nbsp;"
            f"Start Date: <b>{escape(start_date)}</b> &nbsp;&nbsp;"
            f"End Date: <b>{escape(end_date)}</b>", meta_style,
        ),
    ]
    widths = [22, 65, 58, 65, 65, 86, 42, 42, 42, 42, 42]
    table = Table(table_data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#777777")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    balance_table = Table([
        [
            _report_cell(f"Opening Balance: {opening_balance:.2f}", header_style),
            _report_cell(f"Closing Balance: {closing_balance:.2f}", header_style),
        ]
    ], colWidths=[90 * mm, 90 * mm])
    balance_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#777777")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f3f5")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.extend([Spacer(1, 4), balance_table, Spacer(1, 6), table])
    document.build(elements)
    return response
