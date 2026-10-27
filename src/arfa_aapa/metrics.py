"""Governed metrics.

Each metric has exactly one written definition and one fixed SQL template.
The agent may not invent a new metric, a new table, or a new definition.
All money values are in EGP. Only invoiced rows count as revenue.
"""

import sqlite3
from dataclasses import dataclass

from .security import validate_sql


@dataclass(frozen=True)
class MetricResult:
    metric_key: str
    name_ar: str
    definition_ar: str
    value: object
    unit: str
    source_tables: tuple[str, ...]
    row_count: int = 0
    detail: str = ""


def _run(connection: sqlite3.Connection, sql: str, params: dict) -> list[sqlite3.Row]:
    validate_sql(sql)
    return connection.execute(sql, params).fetchall()


def _branch_filter(branch_id: int | None) -> tuple[str, dict]:
    if branch_id is None:
        return "", {}
    return " AND branch_id = :branch_id", {"branch_id": branch_id}


def total_revenue(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    total = 0.0
    for table, date_col, extra in [
        ("sales", "sale_date", " AND status = 'invoiced'"),
        ("parts_sales", "sale_date", ""),
        ("service_job_cards", "opened_date", " AND status IN ('invoiced', 'closed')"),
    ]:
        amount_col = "labor_amount_egp" if table == "service_job_cards" else "amount_egp"
        sql = f"SELECT COALESCE(SUM({amount_col}), 0) AS v FROM {table} WHERE {date_col} BETWEEN :start AND :end{extra}{branch_sql}"
        total += float(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("total_revenue", "إجمالي الإيراد", "مجموع المبيعات المفوترة زائد قطع الغيار زائد أجور الصيانة للكروت المفوترة أو المغلقة، في الفترة المحددة.", round(total, 2), "جنيه", ("sales", "parts_sales", "service_job_cards"))


def sales_revenue(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COALESCE(SUM(amount_egp), 0) AS v FROM sales WHERE sale_date BETWEEN :start AND :end AND status = 'invoiced'{branch_sql}"
    value = float(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("sales_revenue", "إيراد مبيعات السيارات", "مجموع مبيعات السيارات بحالة مفوترة فقط، ولا تشمل الملغاة.", round(value, 2), "جنيه", ("sales",))


def service_revenue(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COALESCE(SUM(labor_amount_egp), 0) AS v FROM service_job_cards WHERE opened_date BETWEEN :start AND :end AND status IN ('invoiced', 'closed'){branch_sql}"
    value = float(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("service_revenue", "إيراد الصيانة", "مجموع أجور الصيانة للكروت المفوترة أو المغلقة فقط.", round(value, 2), "جنيه", ("service_job_cards",))


def parts_revenue(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COALESCE(SUM(amount_egp), 0) AS v FROM parts_sales WHERE sale_date BETWEEN :start AND :end{branch_sql}"
    value = float(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("parts_revenue", "إيراد قطع الغيار", "مجموع مبيعات قطع الغيار في الفترة المحددة.", round(value, 2), "جنيه", ("parts_sales",))


def open_job_cards(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COUNT(*) AS v FROM service_job_cards WHERE opened_date <= :end AND status IN ('open', 'ready'){branch_sql}"
    value = int(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("open_job_cards", "كروت الشغل المفتوحة", "عدد كروت الصيانة بحالة مفتوح أو جاهز للفوترة، حتى نهاية الفترة.", value, "كارت", ("service_job_cards",))


def overdue_job_cards(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COUNT(*) AS v FROM service_job_cards WHERE opened_date <= date(:end, '-14 days') AND status IN ('open', 'ready'){branch_sql}"
    value = int(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("overdue_job_cards", "كروت الشغل المتأخرة", "عدد الكروت المفتوحة أو الجاهزة للفوترة، والتي مر على فتحها أكثر من 14 يوما حتى نهاية الفترة.", value, "كارت", ("service_job_cards",))


def average_satisfaction(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COUNT(*) AS n, COALESCE(AVG(score_1_5), 0) AS v FROM surveys WHERE survey_date BETWEEN :start AND :end{branch_sql}"
    row = _run(connection, sql, {"start": start, "end": end, **branch_params})[0]
    return MetricResult("average_satisfaction", "متوسط رضا العملاء", "متوسط درجات الاستبيان من 1 إلى 5 في الفترة المحددة.", round(float(row["v"]), 2), "من 5", ("surveys",), row_count=int(row["n"]))


def service_hours_efficiency(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COALESCE(SUM(sold_hours), 0) AS sold, COALESCE(SUM(actual_hours), 0) AS actual FROM service_job_cards WHERE opened_date BETWEEN :start AND :end AND status IN ('invoiced', 'closed'){branch_sql}"
    row = _run(connection, sql, {"start": start, "end": end, **branch_params})[0]
    sold, actual = float(row["sold"]), float(row["actual"])
    ratio = round(actual / sold * 100, 1) if sold else 0.0
    return MetricResult("service_hours_efficiency", "كفاءة ساعات الصيانة", "الساعات الفعلية مقسومة على الساعات المباعة، مضروبة في 100، للكروت المفوترة أو المغلقة. فوق 100 يعني وقت فعلي أكثر من المباع.", ratio, "%", ("service_job_cards",), detail=f"ساعات مباعة: {sold}، ساعات فعلية: {actual}.")


def top_selling_part(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT part_name, COALESCE(SUM(amount_egp), 0) AS v FROM parts_sales WHERE sale_date BETWEEN :start AND :end{branch_sql} GROUP BY part_name ORDER BY v DESC LIMIT 1"
    rows = _run(connection, sql, {"start": start, "end": end, **branch_params})
    if not rows:
        return MetricResult("top_selling_part", "أكثر قطعة غيار مبيعا", "قطعة الغيار الأعلى إيرادا في الفترة المحددة.", None, "جنيه", ("parts_sales",))
    row = rows[0]
    return MetricResult("top_selling_part", "أكثر قطعة غيار مبيعا", "قطعة الغيار الأعلى إيرادا في الفترة المحددة.", row["part_name"], "جنيه", ("parts_sales",), detail=f"إيرادها: {round(float(row['v']), 2)} جنيه.")


def low_stock_parts(connection, branch_id, start, end):
    branch_sql, branch_params = _branch_filter(branch_id)
    sql = f"SELECT COUNT(*) AS v FROM parts_inventory WHERE stock_qty <= reorder_level{branch_sql}"
    value = int(_run(connection, sql, {"start": start, "end": end, **branch_params})[0]["v"])
    return MetricResult("low_stock_parts", "أصناف قطع الغيار تحت حد إعادة الطلب", "عدد أصناف المخزون التي وصل مخزونها إلى حد إعادة الطلب أو أقل منه.", value, "صنف", ("parts_inventory",))


def best_branch(connection, branch_id, start, end):
    sql = """
        SELECT b.name AS branch_name, COALESCE(SUM(s.amount_egp), 0) AS v
        FROM branches b LEFT JOIN sales s
          ON s.branch_id = b.id AND s.sale_date BETWEEN :start AND :end AND s.status = 'invoiced'
        GROUP BY b.id, b.name ORDER BY v DESC LIMIT 1
    """
    rows = _run(connection, sql, {"start": start, "end": end})
    if not rows:
        return MetricResult("best_branch", "أفضل فرع في مبيعات السيارات", "الفرع الأعلى إيرادا من مبيعات السيارات المفوترة في الفترة المحددة.", None, "جنيه", ("branches", "sales"))
    row = rows[0]
    return MetricResult("best_branch", "أفضل فرع في مبيعات السيارات", "الفرع الأعلى إيرادا من مبيعات السيارات المفوترة في الفترة المحددة.", row["branch_name"], "جنيه", ("branches", "sales"), detail=f"إيراده: {round(float(row['v']), 2)} جنيه.")


METRICS = {
    "total_revenue": total_revenue,
    "sales_revenue": sales_revenue,
    "service_revenue": service_revenue,
    "parts_revenue": parts_revenue,
    "open_job_cards": open_job_cards,
    "overdue_job_cards": overdue_job_cards,
    "average_satisfaction": average_satisfaction,
    "service_hours_efficiency": service_hours_efficiency,
    "top_selling_part": top_selling_part,
    "low_stock_parts": low_stock_parts,
    "best_branch": best_branch,
}
