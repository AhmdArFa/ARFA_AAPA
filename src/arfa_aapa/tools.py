"""Tools registry for the unified agent. Stdlib only.

A tool is a governed, evidence-carrying operation. It is not a free SQL
endpoint, not a model call, and not a prompt. Each tool has:
- name, domain, description in Arabic
- parameters it accepts, all from fixed registries, never free text SQL
- a run function that returns an answer with value, definition, sources,
  and evidence, or an abstention.
If a tool is not registered here, the unified agent cannot call it.
"""
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ToolSpec:
    name: str
    domain: str
    description_ar: str
    parameters: tuple
    evidence_fields: tuple

TOOLS = [
    ToolSpec("sales_revenue", "sales", "إيراد مبيعات السيارات المفوترة، مع فترة وفرع اختياري", ("period", "branch"), ("value", "definition", "source_tables")),
    ToolSpec("service_job_cards", "service", "كروت الصيانة، عددها وحالتها ونوعها، مع فترة وفرع", ("period", "branch", "dimension"), ("value", "rows", "definition", "source_tables")),
    ToolSpec("parts_sales", "parts", "مبيعات قطع الغيار، إجمالي ومتوسط وعدد، حسب القطعة أو الفرع", ("period", "branch", "dimension"), ("value", "rows", "definition", "source_tables")),
    ToolSpec("customer_satisfaction", "survey", "متوسط رضا العملاء من الاستبيانات، مع فترة وفرع", ("period", "branch"), ("value", "definition", "source_tables")),
    ToolSpec("crm_leads", "crm", "عدد العملاء المحتملين حسب المصدر أو الحالة، من غير أسماء", ("period", "branch", "dimension"), ("value", "rows", "definition", "source_tables")),
    ToolSpec("accounting_invoices", "accounting", "فواتير المحاسبة، مدفوعة ومتأخرة وغير مدفوعة، مع فترة وفرع", ("period", "branch", "dimension"), ("value", "rows", "definition", "source_tables")),
    ToolSpec("cars_inventory", "cars", "مخزون السيارات، عدد وقيمة حسب الموديل أو الحالة", ("branch", "dimension"), ("value", "rows", "definition", "source_tables")),
    ToolSpec("company_profit", "accounting", "ربح تجريبي = إيراد مفوتر ناقص تكاليف مسجلة، مع تحذير أن تكلفة شراء السيارات غير مسجلة", ("period", "branch"), ("value", "revenue", "costs_by_category", "margin_percent", "caveat", "source_tables")),
    ToolSpec("warehouse_stock", "parts", "مخزون قطع الغيار، كمية وقيمة وأصناف تحت حد إعادة الطلب، لقطة حالية", ("branch", "part"), ("parts_stock_qty", "parts_inventory_value", "parts_low_stock_rows", "by_part", "cars_available", "source_tables")),
    ToolSpec("employee_performance", "employees", "أداء موظف محدد لمدير الشركة فقط: دور وفرع ومبيعات أو كروت صيانة، من غير مرتب أو هاتف", ("employee_name",), ("role", "branch", "sales_invoiced", "job_cards", "source_tables")),
    ToolSpec("trial_log_review", "trial", "مراجعة الأسئلة غير المجابة في التجربة، للمراجعة بعد التجربة فقط، لا تضيف مقاييس تلقائيا", (), ("trial_log",)),
]

TOOL_INDEX = {t.name: t for t in TOOLS}

def list_tools():
    return TOOLS

def get_tool(name: str):
    return TOOL_INDEX.get(name)
