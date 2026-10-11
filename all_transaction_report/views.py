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


def _balance_sql(alias="d"):
    """Return receive minus payment for the rows matched by the report filters."""
    return f"""
        COALESCE(SUM(COALESCE({alias}.receive, 0)), 0)
        - COALESCE(SUM(COALESCE({alias}.payment, 0)), 0)
    """


def all_transaction_report(request):
    today = timezone.localdate().isoformat()
    main_head = (request.GET.get("main_head") or "").strip()
    start_date = (request.GET.get("start_date") or today).strip()
    end_date = (request.GET.get("end_date") or today).strip()

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

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT
            d.id, d.tran_id, COALESCE(d.invoice_ref, '') AS invoice_ref,
            d.tran_date,
            COALESCE(mh.type_name, CAST(d.tran_type AS CHAR)) AS main_head_name,
            COALESCE(th.tran_head_name, '') AS tran_head_name,
            COALESCE(tw.tran_with_name, CAST(d.tran_type_with AS CHAR), '') AS tran_with_name,
            COALESCE(m.tran_user, d.tran_user, '') AS tran_user,
            COALESCE(m.user_name, d.user_name, '') AS user_name,
            COALESCE(m.tran_by, d.tran_by, '') AS tran_by,
            COALESCE(doc.name, m.doctor_id, '') AS doctor_name,
            COALESCE(sr.name, m.sr_id, '') AS sr_name,
            COALESCE(patient_user.user_name, m.patient_id, '') AS patient_name,
            d.tran_method,
            COALESCE(d.amount, 0) AS bill_amount,
            COALESCE(d.discount, 0) AS discount,
            COALESCE(d.tot_amount, d.amount, 0) AS net_amount,
            COALESCE(d.receive, 0) AS receive,
            COALESCE(d.payment, 0) AS payment,
            COALESCE(d.due_col, 0) AS due_col,
            COALESCE(d.due_disc, 0) AS due_disc,
            COALESCE(d.payment_mode, '') AS payment_mode
        FROM transaction__details d
        LEFT JOIN transaction__mains m ON m.tran_id = d.tran_id
        LEFT JOIN transaction__main__heads mh ON mh.id = m.tran_type
        LEFT JOIN transaction__heads th ON th.id = d.tran_head_id
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN doctors_info doc ON doc.custom_doc_id = m.doctor_id
        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id = m.sr_id
        LEFT JOIN user__infos patient_user ON patient_user.user_id = m.patient_id
        WHERE {where_sql}
        ORDER BY d.tran_type ASC, d.tran_date ASC, d.id ASC
    """

    opening_where = ["1 = 1"]
    opening_params = []
    if main_head:
        opening_where.append("d.tran_type = %s")
        opening_params.append(main_head)
    if start_date:
        opening_where.append("d.tran_date < %s")
        opening_params.append(start_date)
    else:
        opening_where.append("1 = 0")

    opening_sql = f"""
        SELECT {_balance_sql('d')}
        FROM transaction__details d
        WHERE {' AND '.join(opening_where)}
    """

    closing_where = ["1 = 1", "d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)"]
    closing_params = [end_date]
    if main_head:
        closing_where.insert(1, "d.tran_type = %s")
        closing_params.insert(0, main_head)
    closing_sql = f"""
        SELECT {_balance_sql('d')}
        FROM transaction__details d
        WHERE {' AND '.join(closing_where)}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in rows]
        totals = {
            key: sum(float(row.get(key) or 0) for row in rows)
            for key in ("bill_amount", "discount", "net_amount", "receive", "payment", "due_col", "due_disc")
        }
        cursor.execute(opening_sql, opening_params)
        opening_balance = float(cursor.fetchone()[0] or 0)
        cursor.execute(closing_sql, closing_params)
        closing_balance = float(cursor.fetchone()[0] or 0)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, type_name
            FROM transaction__main__heads
            ORDER BY type_name ASC
        """)
        main_heads = cursor.fetchall()

    return render(request, "all_transaction_report/report.html", {
        "rows": rows,
        "main_heads": main_heads,
        "selected_main_head": main_head,
        "start_date": start_date,
        "end_date": end_date,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "totals": totals,
    })


def all_transaction_report_pdf(request):
    today = timezone.localdate().isoformat()
    main_head = (request.GET.get("main_head") or "").strip()
    start_date = (request.GET.get("start_date") or today).strip()
    end_date = (request.GET.get("end_date") or today).strip()

    where = ["1 = 1"]
    params = []
    if main_head:
        where.append("d.tran_type = %s")
        params.append(main_head)
    where.append("d.tran_date >= %s")
    params.append(start_date)
    where.append("d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)")
    params.append(end_date)
    where_sql = " AND ".join(where)

    sql = f"""
        SELECT d.tran_id, COALESCE(d.invoice_ref, ''), d.tran_date,
               COALESCE(mh.type_name, CAST(d.tran_type AS CHAR)),
               COALESCE(th.tran_head_name, ''),
               COALESCE(tw.tran_with_name, CAST(d.tran_type_with AS CHAR), ''),
               COALESCE(m.tran_user, d.tran_user, ''), COALESCE(m.user_name, d.user_name, ''),
               COALESCE(doc.name, m.doctor_id, ''), COALESCE(sr.name, m.sr_id, ''),
               COALESCE(patient_user.user_name, m.patient_id, ''),
               COALESCE(d.tran_by, ''), COALESCE(d.tran_method, ''),
               COALESCE(d.amount, 0), COALESCE(d.discount, 0),
               COALESCE(d.tot_amount, d.amount, 0), COALESCE(d.receive, 0),
               COALESCE(d.payment, 0), COALESCE(d.due_col, 0),
               COALESCE(d.due_disc, 0)
        FROM transaction__details d
        LEFT JOIN transaction__mains m ON m.tran_id = d.tran_id
        LEFT JOIN transaction__main__heads mh ON mh.id = m.tran_type
        LEFT JOIN transaction__heads th ON th.id = d.tran_head_id
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN doctors_info doc ON doc.custom_doc_id = m.doctor_id
        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id = m.sr_id
        LEFT JOIN user__infos patient_user ON patient_user.user_id = m.patient_id
        WHERE {where_sql}
        ORDER BY d.tran_type ASC, d.tran_date ASC, d.id ASC
    """

    opening_where = ["1 = 1"]
    opening_params = []
    if main_head:
        opening_where.append("d.tran_type = %s")
        opening_params.append(main_head)
    opening_where.append("d.tran_date < %s")
    opening_params.append(start_date)
    opening_sql = f"""
        SELECT {_balance_sql('d')}
        FROM transaction__details d
        WHERE {' AND '.join(opening_where)}
    """
    closing_where = ["1 = 1", "d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)"]
    closing_params = [end_date]
    if main_head:
        closing_where.insert(1, "d.tran_type = %s")
        closing_params.insert(0, main_head)
    closing_sql = f"""
        SELECT {_balance_sql('d')}
        FROM transaction__details d
        WHERE {' AND '.join(closing_where)}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.execute(opening_sql, opening_params)
        opening_balance = float(cursor.fetchone()[0] or 0)
        cursor.execute(closing_sql, closing_params)
        closing_balance = float(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT type_name FROM transaction__main__heads WHERE id = %s",
            [main_head or 0],
        )
        selected_name = cursor.fetchone()
        selected_name = selected_name[0] if selected_name else "All Main Heads"

    def cell(value, header=False):
        style = ParagraphStyle(
            "report_header" if header else "report_cell",
            parent=getSampleStyleSheet()["Normal"],
            fontName="Helvetica-Bold" if header else "Helvetica",
            fontSize=7 if header else 6.5,
            leading=8,
            alignment=1 if header else 0,
        )
        return Paragraph(escape(str(value if value is not None else "")), style)

    headers = [
        "SL", "Tran ID", "Invoice Ref", "Date", "Main Head", "Product",
        "Transaction With",
        "Tran User", "User Name", "Doctor", "SR", "Patient", "Transaction By",
        "Method", "Bill", "Discount", "Net", "Receive", "Payment",
        "Due Col", "Due Disc",
    ]
    table_data = [[cell(header, True) for header in headers]]
    for index, row in enumerate(rows, 1):
        values = [index, row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                  row[7], row[8], row[9], row[10], row[11], row[12]]
        values += [f"{float(value or 0):.2f}" for value in row[13:]]
        table_data.append([cell(value) for value in values])
    if rows:
        total_values = ["", "", "", "", "", "", "", "", "", "", "", "", "", "Total"]
        total_values += [f"{sum(float(row[column] or 0) for row in rows):.2f}" for column in
                         (13, 14, 15, 16, 17, 18, 19)]
        table_data.append([cell(value, True) for value in total_values])
    if not rows:
        table_data.append([cell("No transactions found")] + [""] * (len(headers) - 1))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="all_transaction_report.pdf"'
    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "report_title", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=14, leading=17, alignment=1, spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "report_meta", parent=styles["Normal"], fontSize=8, leading=10,
        alignment=1, spaceAfter=5,
    )
    elements = [
        Paragraph("All Transaction Report", title_style),
        Paragraph(
            f"Main Head: <b>{escape(str(selected_name))}</b> &nbsp;&nbsp; "
            f"Start Date: <b>{escape(start_date)}</b> &nbsp;&nbsp; "
            f"End Date: <b>{escape(end_date)}</b>",
            meta_style,
        ),
    ]
    widths = [20, 48, 44, 58, 44, 44, 54, 34, 48, 44, 32, 44, 44, 36] + [30.5] * 7
    table = Table(table_data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#777777")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d9edf7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    balance_style = ParagraphStyle(
        "balance", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=12, alignment=0,
    )
    balance_table = Table([[
        Paragraph(f"Opening Balance: {opening_balance:.2f}", balance_style),
        Paragraph(f"Closing Balance: {closing_balance:.2f}", balance_style),
    ]], colWidths=[398, 398])
    balance_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8c0c8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8c0c8")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f6f7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.extend([balance_table, Spacer(1, 8), table])
    document.build(elements)
    return response
