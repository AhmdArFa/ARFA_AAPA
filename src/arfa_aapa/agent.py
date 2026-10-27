"""Head-manager Business Q&A agent, demo edition.

The agent does not write SQL from the user question and does not calculate.
It routes the question to one governed metric, the database calculates,
and the answer is returned with its source, period and definition.
Unknown, ambiguous or sensitive questions are refused with an abstention.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .data.database import get_connection, reference_date
from .metrics import METRICS

BRANCHES = {
    "القاهره الجديده": 1,
    "القاهره": 1,
    "الجيزه": 2,
    "الاسكندريه": 3,
    "الاسكندريه": 3,
}


@dataclass
class Answer:
    question: str
    metric_key: str | None
    text: str
    confirmed: bool
    period_label: str
    definition: str = ""
    source_tables: tuple[str, ...] = ()
    missing: str = ""
    metric_name: str = ""
    value: object = None
    unit: str = ""
    detail: str = ""


def _normalize(text: str) -> str:
    text = re.sub(r"[\u064b-\u0652]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"[^\w\s]", " ", text).lower()


def _period(normalized: str, reference: date) -> tuple[str, str, str]:
    if "اخر 90 يوم" in normalized or "آخر 90 يوم" in normalized or "90 يوم" in normalized:
        return "آخر 90 يوم", (reference - timedelta(days=89)).isoformat(), reference.isoformat()
    if "الشهر ده" in normalized or "هذا الشهر" in normalized or "الشهر الحالي" in normalized:
        start = reference.replace(day=1)
        return "الشهر الحالي", start.isoformat(), reference.isoformat()
    if "الشهر اللي فات" in normalized or "الشهر الماضي" in normalized:
        first_this_month = reference.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return "الشهر الماضي", last_month_start.isoformat(), last_month_end.isoformat()
    if "كل الفتره" in normalized or "من اول السنه" in normalized or "كل الفترة" in normalized:
        return "كل فترة الداتا التجريبية", "2026-01-01", reference.isoformat()
    return "آخر 30 يوم", (reference - timedelta(days=29)).isoformat(), reference.isoformat()


def _branch_id(normalized: str) -> int | None:
    for name, branch_id in BRANCHES.items():
        if name in normalized:
            return branch_id
    return None


def _route(normalized: str) -> str | None:
    # Most specific questions first, so a general revenue question cannot
    # swallow a more specific one.
    if "اكثر قطعه" in normalized or "اكثر قطعة" in normalized or "اعلى قطعه" in normalized:
        return "top_selling_part"
    if "تحت حد" in normalized or "ناقص" in normalized and "مخزون" in normalized or "مخزون منخفض" in normalized:
        return "low_stock_parts"
    if "متاخر" in normalized:
        return "overdue_job_cards"
    if ("كروت" in normalized or "كارت" in normalized) and "مفتوح" in normalized:
        return "open_job_cards"
    if "رضا" in normalized or "استبيان" in normalized or "تقييم العملاء" in normalized:
        return "average_satisfaction"
    if "ساعات" in normalized and ("فعليه" in normalized or "مباعه" in normalized or "كفاءه" in normalized):
        return "service_hours_efficiency"
    if "افضل فرع" in normalized or "أفضل فرع" in normalized:
        return "best_branch"
    if "اجمالي" in normalized or "إجمالي" in normalized or "كل الايراد" in normalized:
        return "total_revenue"
    if "مبيعات السيارات" in normalized or "بيع السيارات" in normalized:
        return "sales_revenue"
    if "صيانه" in normalized or "خدمه" in normalized:
        return "service_revenue"
    if "قطع الغيار" in normalized or "قطع غيار" in normalized:
        return "parts_revenue"
    return None


def _abstain(question: str, period_label: str, reason: str) -> Answer:
    return Answer(
        question=question,
        metric_key=None,
        text=f"مش عارف أجاوب على السؤال ده من الداتا التجريبية المعتمدة. السبب: {reason} لو توضح السؤال أو تختار مقياسا معتمدا، أقدر أجاوب.",
        confirmed=False,
        period_label=period_label,
        missing=reason,
    )


def ask(question: str, db_path: Path | None = None) -> Answer:
    normalized = _normalize(question)
    connection = get_connection(db_path)
    try:
        reference = date.fromisoformat(reference_date(connection))
        period_label, start, end = _period(normalized, reference)
        branch_id = _branch_id(normalized)

        if any(word in normalized for word in ["مرتب", "راتب", "هاتف", "تليفون", "كلمه سر", "باسورد"]):
            return _abstain(question, period_label, "السؤال يطلب بيانات حساسة خارج المقاييس المعتمدة.")

        metric_key = _route(normalized)
        if metric_key is None:
            return _abstain(question, period_label, "السؤال مش مربوط بمقياس معتمد في النسخة التجريبية.")

        result = METRICS[metric_key](connection, branch_id, start, end)
        if result.value is None:
            return _abstain(question, period_label, "لا توجد داتا كافية في الفترة المحددة لهذا المقياس.")
        branch_text = f" للفرع رقم {branch_id}" if branch_id else ""
        if metric_key in ("top_selling_part", "best_branch"):
            value_text = f"{result.value}. {result.detail}"
            period_text = f"في {period_label} ({start} إلى {end})"
        elif metric_key == "low_stock_parts":
            value_text = f"{result.value} {result.unit}."
            period_text = "حاليا"
        else:
            value_text = f"{result.value} {result.unit}."
            period_text = f"في {period_label} ({start} إلى {end})"
        text = (
            f"{result.name_ar}{branch_text} {period_text}: "
            f"{value_text} "
            f"التعريف: {result.definition_ar} المصدر: {', '.join(result.source_tables)}."
        )
        return Answer(
            question=question,
            metric_key=metric_key,
            text=text,
            confirmed=True,
            period_label=period_label,
            definition=result.definition_ar,
            source_tables=result.source_tables,
            metric_name=result.name_ar,
            value=result.value,
            unit=result.unit,
            detail=result.detail,
        )
    finally:
        connection.close()
