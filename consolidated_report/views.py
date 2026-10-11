from django.db import connection
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from xml.sax.saxutils import escape


NUMERIC_FIELDS = ("bill_amount", "discount", "net_amount", "receive", "payment", "due", "due_col", "due_disc")


def _filters(request):
    today = timezone.localdate().isoformat()
    main_head = (request.GET.get("main_head") or "").strip()
    start_date = (request.GET.get("start_date") or today).strip()
    end_date = (request.GET.get("end_date") or today).strip()
    where = ["1 = 1"]
    params = []
    if main_head:
        where.append("d.tran_type = %s")
        params.append(main_head)
    where += ["d.tran_date >= %s", "d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)"]
    params += [start_date, end_date]
    return main_head, start_date, end_date, where, params


def _query(where_sql, params):
    sql = f"""
        SELECT
            MIN(d.id) AS id,
            d.tran_id,
            COALESCE(MAX(d.invoice_ref), '') AS invoice_ref,
            MIN(d.tran_date) AS tran_date,
            COALESCE(MAX(mh.type_name), CAST(MAX(d.tran_type) AS CHAR)) AS main_head_name,
            COALESCE(MAX(tw.tran_with_name), CAST(MAX(d.tran_type_with) AS CHAR), '') AS tran_with_name,
            COALESCE(MAX(m.tran_user), MAX(d.tran_user), '') AS tran_user,
            COALESCE(MAX(m.user_name), MAX(d.user_name), '') AS user_name,
            COALESCE(MAX(doc.name), MAX(m.doctor_id), '') AS doctor_name,
            COALESCE(MAX(sr.name), MAX(m.sr_id), '') AS sr_name,
            COALESCE(MAX(patient_user.user_name), MAX(m.patient_id), '') AS patient_name,
            COALESCE(MAX(m.tran_by), MAX(d.tran_by), '') AS tran_by,
            COALESCE(MAX(d.tran_method), '') AS tran_method,
            COALESCE(SUM(d.amount), 0) AS bill_amount,
            COALESCE(SUM(d.discount), 0) AS discount,
            COALESCE(SUM(COALESCE(d.amount, 0) - COALESCE(d.discount, 0)), 0) AS net_amount,
            COALESCE(SUM(d.receive), 0) AS receive,
            COALESCE(SUM(d.payment), 0) AS payment,
            COALESCE(SUM(d.due), 0) AS due,
            COALESCE(SUM(d.due_col), 0) AS due_col,
            COALESCE(SUM(d.due_disc), 0) AS due_disc
        FROM transaction__details d
        LEFT JOIN transaction__mains m ON m.tran_id = d.tran_id
        LEFT JOIN transaction__main__heads mh ON mh.id = d.tran_type
        LEFT JOIN transaction__withs tw ON tw.id = d.tran_type_with
        LEFT JOIN doctors_info doc ON doc.custom_doc_id = m.doctor_id
        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id = m.sr_id
        LEFT JOIN user__infos patient_user ON patient_user.user_id = m.patient_id
        WHERE {where_sql}
        GROUP BY d.tran_id
        ORDER BY MIN(d.tran_type), MIN(d.tran_date), MIN(d.id)
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _balance(where, params):
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COALESCE(SUM(d.receive), 0) - COALESCE(SUM(d.payment), 0) "
            f"FROM transaction__details d WHERE {' AND '.join(where)}", params
        )
        return float(cursor.fetchone()[0] or 0)


def consolidated_report(request):
    main_head, start_date, end_date, where, params = _filters(request)
    rows = _query(" AND ".join(where), params)
    opening_where = ["1 = 1"]
    opening_params = []
    if main_head:
        opening_where.append("d.tran_type = %s")
        opening_params.append(main_head)
    opening_where.append("d.tran_date < %s")
    opening_params.append(start_date)
    opening_balance = _balance(opening_where, opening_params)
    closing_where = ["1 = 1", "d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)"]
    closing_params = [end_date]
    if main_head:
        closing_where.insert(1, "d.tran_type = %s")
        closing_params.insert(0, main_head)
    closing_balance = _balance(closing_where, closing_params)
    totals = {key: sum(float(row.get(key) or 0) for row in rows) for key in NUMERIC_FIELDS}
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, type_name FROM transaction__main__heads ORDER BY type_name")
        main_heads = cursor.fetchall()
    return render(request, "consolidated_report/list.html", {
        "rows": rows, "main_heads": main_heads, "selected_main_head": main_head,
        "start_date": start_date, "end_date": end_date,
        "opening_balance": opening_balance, "closing_balance": closing_balance,
        "totals": totals,
    })


def consolidated_report_pdf(request):
    main_head, start_date, end_date, where, params = _filters(request)
    rows = _query(" AND ".join(where), params)
    headers = ["SL", "Tran ID", "Invoice Ref", "Date", "Main Head", "Transaction With", "Method", "Bill", "Discount", "Net", "Receive", "Payment", "Due", "Due Col", "Due Disc"]
    data = [headers]
    for index, row in enumerate(rows, 1):
        data.append([index, row["tran_id"], row["invoice_ref"], row["tran_date"], row["main_head_name"], row["tran_with_name"], row["tran_method"]] + [f'{float(row[key] or 0):.2f}' for key in NUMERIC_FIELDS])
    totals = {key: sum(float(row.get(key) or 0) for row in rows) for key in NUMERIC_FIELDS}
    if rows:
        data.append(["", "", "", "", "", "", "Total"] + [f'{totals[key]:.2f}' for key in NUMERIC_FIELDS])
    if not rows:
        data.append(["No transactions found"] + [""] * (len(headers) - 1))

    opening_where = ["1 = 1", "d.tran_date < %s"]
    opening_params = [start_date]
    if main_head:
        opening_where.insert(1, "d.tran_type = %s")
        opening_params.insert(0, main_head)
    opening_balance = _balance(opening_where, opening_params)
    closing_where = ["1 = 1", "d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)"]
    closing_params = [end_date]
    if main_head:
        closing_where.insert(1, "d.tran_type = %s")
        closing_params.insert(0, main_head)
    closing_balance = _balance(closing_where, closing_params)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="consolidated_report.pdf"'
    document = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=22 * 2.834, leftMargin=22 * 2.834, topMargin=14 * 2.834, bottomMargin=14 * 2.834)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ConsolidatedTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=14, leading=17, alignment=1, spaceAfter=8)
    meta = ParagraphStyle("ConsolidatedMeta", parent=styles["Normal"], fontSize=8, leading=10, alignment=1, spaceAfter=5)
    selected_name = "All Main Heads"
    if main_head:
        with connection.cursor() as cursor:
            cursor.execute("SELECT type_name FROM transaction__main__heads WHERE id = %s", [main_head])
            selected = cursor.fetchone()
        selected_name = selected[0] if selected else main_head
    def cell(value, header=False):
        style = ParagraphStyle("consolidated_header" if header else "consolidated_cell", parent=styles["Normal"], fontName="Helvetica-Bold" if header else "Helvetica", fontSize=7 if header else 6.5, leading=8, alignment=1 if header else 0)
        return Paragraph(escape(str(value if value is not None else "")), style)
    table_data = [[cell(value, True) for value in data[0]]]
    table_data += [[cell(value) for value in row] for row in data[1:-1]]
    table_data.append([cell(value, bool(rows)) for value in data[-1]])
    table = Table(table_data, colWidths=[25, 65, 65, 70, 60, 85, 45] + [47.625] * 8, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .35, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d9edf7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    balance_style = ParagraphStyle("ConsolidatedBalance", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12, alignment=0)
    balance_table = Table([[Paragraph(f"Opening Balance: {opening_balance:.2f}", balance_style), Paragraph(f"Closing Balance: {closing_balance:.2f}", balance_style)]], colWidths=[398, 398])
    balance_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .35, colors.grey),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f3f5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    document.build([
        Paragraph("Consolidated Report", title),
        Paragraph(f"Main Head: <b>{escape(str(selected_name))}</b> &nbsp;&nbsp; Start Date: <b>{start_date}</b> &nbsp;&nbsp; End Date: <b>{end_date}</b>", meta),
        balance_table,
        Spacer(1, 8),
        table,
    ])
    return response
