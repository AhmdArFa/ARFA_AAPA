"""Company-domain engine, trial mode. Stdlib only, read-only SQLite.

One domain + one measure + at most one dimension + period + branch.
SQL is built only from the registry below, never from user words.
If anything is unregistered, or sensitive, the engine abstains and lists
the available domains. See docs/company-domains/design.md.
"""
import re, sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRANCHES = {"القاهره": 1, "القاهره الجديده": 1, "الجيزه": 2, "الاسكندريه": 3,
            "cairo": 1, "giza": 2, "alexandria": 3}
AVAILABLE = ["sales", "service", "parts", "survey", "crm", "accounting", "cars"]
UNREGISTERED = ["عقار", "مطعم", "فندق", "طيران", "صيدل", "مستشف", "real estate"]
SENSITIVE = ["مرتب", "راتب", "هاتف", "تليفون", "اسم عميل", "اسم العميل", "كلمه سر", "باسورد",
             "salary", "phone", "password", "customer_name", "national_id"]

@dataclass(frozen=True)
class Domain:
    key: str
    name_ar: str
    table: str
    date_col: str
    amount_col: str | None
    # measure -> (sql template fragment, definition)
    measures: dict
    dimensions: dict  # dimension key -> sql column or expression

DOMAINS = {
    "sales": Domain("sales", "المبيعات", "sales", "sale_date", "amount_egp",
        {"count": ("COUNT(*)", "عدد مبيعات السيارات المفوترة"),
         "sum": ("SUM(amount_egp)", "مجموع إيراد مبيعات السيارات المفوترة"),
         "avg": ("AVG(amount_egp)", "متوسط قيمة مبيعات السيارات المفوترة")},
        {"branch": "branch_id", "model": "vehicle_model", "month": "substr(sale_date, 1, 7)", "status": "status"}),
    "service": Domain("service", "الصيانة", "service_job_cards", "opened_date", "labor_amount_egp",
        {"count": ("COUNT(*)", "عدد كروت الصيانة"),
         "sum": ("SUM(labor_amount_egp)", "مجموع أجور الصيانة"),
         "avg": ("AVG(labor_amount_egp)", "متوسط أجر الصيانة")},
        {"branch": "branch_id", "type": "service_type", "status": "status", "month": "substr(opened_date, 1, 7)"}),
    "parts": Domain("parts", "قطع الغيار", "parts_sales", "sale_date", "amount_egp",
        {"count": ("COUNT(*)", "عدد مبيعات قطع الغيار"),
         "sum": ("SUM(amount_egp)", "مجموع مبيعات قطع الغيار"),
         "avg": ("AVG(amount_egp)", "متوسط قيمة مبيعات قطع الغيار")},
        {"branch": "branch_id", "part": "part_name", "month": "substr(sale_date, 1, 7)"}),
    "survey": Domain("survey", "الاستبيانات", "surveys", "survey_date", "score_1_5",
        {"count": ("COUNT(*)", "عدد الاستبيانات"),
         "avg": ("AVG(score_1_5)", "متوسط درجة الاستبيان من 1 إلى 5")},
        {"branch": "branch_id", "month": "substr(survey_date, 1, 7)"}),
    "crm": Domain("crm", "إدارة العملاء", "crm_leads", "created_date", None,
        {"count": ("COUNT(*)", "عدد العملاء المحتملين")},
        {"branch": "branch_id", "source": "source", "status": "status", "month": "substr(created_date, 1, 7)"}),
    "accounting": Domain("accounting", "المحاسبة", "accounting_invoices", "invoice_date", "amount_egp",
        {"count": ("COUNT(*)", "عدد الفواتير"),
         "sum": ("SUM(amount_egp)", "مجموع مبالغ الفواتير"),
         "avg": ("AVG(amount_egp)", "متوسط قيمة الفواتير")},
        {"branch": "branch_id", "status": "status", "month": "substr(invoice_date, 1, 7)"}),
    "cars": Domain("cars", "مخزون السيارات", "cars_inventory", None, "price_egp",
        {"count": ("COUNT(*)", "عدد السيارات في المخزون"),
         "sum": ("SUM(price_egp)", "مجموع أسعار السيارات في المخزون")},
        {"branch": "branch_id", "model": "vehicle_model", "status": "status"}),
}
# Special filters, registered only, never from user text
SPECIAL = {
    ("sales", "sum"): " AND status = 'invoiced'",
    ("sales", "count"): " AND status = 'invoiced'",
    ("sales", "avg"): " AND status = 'invoiced'",
    ("accounting", "sum_paid"): " AND status = 'paid'",
}

@dataclass
class CompanyAnswer:
    question: str
    domain: str | None
    confirmed: bool
    text: str
    value: object = None
    rows: list = None
    definition: str = ""
    source_tables: tuple = ()
    missing: str = ""

def _norm(t: str) -> str:
    t = re.sub(r"[\u064b-\u0652]", "", t)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"[^\w\s]", " ", t).lower()

def _period(q: str, ref: date):
    if "اخر 90 يوم" in q or "90 يوم" in q or "last 90" in q:
        return "آخر 90 يوم", (ref - timedelta(days=89)).isoformat(), ref.isoformat()
    if "الشهر الحالي" in q or "الشهر ده" in q or "current month" in q:
        return "الشهر الحالي", ref.replace(day=1).isoformat(), ref.isoformat()
    if "الشهر الماضي" in q or "الشهر اللي فات" in q or "last month" in q:
        first = ref.replace(day=1); last_end = first - timedelta(days=1)
        return "الشهر الماضي", last_end.replace(day=1).isoformat(), last_end.isoformat()
    if "فتره" in q or "all period" in q or "all time" in q:
        return "كل فترة الداتا التجريبية", "2026-01-01", ref.isoformat()
    return "آخر 30 يوم", (ref - timedelta(days=29)).isoformat(), ref.isoformat()

def _domain(q: str) -> str | None:
    if any(w in q for w in ["بشر", "موظف", "human resources"]):
        return None
    if "قطع" in q: return "parts"
    if any(w in q for w in ["صيان", "كروت", "service"]): return "service"
    if any(w in q for w in ["استبيان", "رضا", "survey"]): return "survey"
    if any(w in q for w in ["محتمل", "crm", "lead"]): return "crm"
    if any(w in q for w in ["محاسب", "فواتير", "invoice", "accounting"]): return "accounting"
    if ("سيارات" in q and "مخزون" in q) or "inventory" in q: return "cars"
    if any(w in q for w in ["مبيعات", "بيع", "sales"]): return "sales"
    return None

def _measure(q: str) -> str | None:
    if any(w in q for w in ["متوسط", "average", "avg"]): return "avg"
    if any(w in q for w in ["اجمالي", "إجمالي", "مجموع", "total", "sum"]): return "sum"
    if any(w in q for w in ["عدد", "كم", "count", "how many"]): return "count"
    return None

def _dimension(q: str, dom: Domain) -> str | None:
    if "حسب" not in q and "by " not in q and "per " not in q:
        return None
    if "فرع" in q or "branch" in q: return "branch"
    if "شهر" in q or "month" in q: return "month"
    if "نوع" in q or "type" in q: return "type"
    if "موديل" in q or "model" in q: return "model"
    if "حال" in q or "status" in q: return "status"
    if "مصدر" in q or "source" in q: return "source"
    if "قطع" in q and dom.key == "parts": return "part"
    return None

def _branch(q: str):
    for name, bid in BRANCHES.items():
        if name in q: return bid
    return None

class CompanyEngine:
    def __init__(self, db_path: Path | None = None):
        self.path = Path(db_path) if db_path else HERE / "company.db"
        if not self.path.exists():
            raise FileNotFoundError(f"Company demo database not found: {self.path}. Run: python3 seed_company.py")
        self.trial_log: list = []
    def _ref(self, con) -> date:
        row = con.execute("SELECT MAX(sale_date) FROM sales").fetchone()
        return date.fromisoformat(row[0])
    def ask(self, question: str) -> CompanyAnswer:
        q = _norm(question)
        if any(w in q for w in UNREGISTERED):
            a = CompanyAnswer(question, None, False,
                f"امتناع: هذا المجال غير مسجل في الشركة في الديمو. المجالات المتاحة: {', '.join(AVAILABLE)}.",
                missing="مجال غير مسجل")
            self.trial_log.append((question, a.missing)); return a
        if any(w in q for w in SENSITIVE):
            a = CompanyAnswer(question, None, False, "امتناع: السؤال يطلب بيانات حساسة خارج المجالات المعتمدة.", missing="بيانات حساسة")
            self.trial_log.append((question, a.missing)); return a
        dom_key = _domain(q)
        if dom_key is None:
            a = CompanyAnswer(question, None, False,
                f"امتناع: المجال غير مسجل في الديمو. المجالات المتاحة: {', '.join(AVAILABLE)}.",
                missing="مجال غير مسجل")
            self.trial_log.append((question, a.missing)); return a
        dom = DOMAINS[dom_key]
        meas = _measure(q)
        if meas is None or meas not in dom.measures:
            a = CompanyAnswer(question, dom_key, False,
                f"امتناع: المقياس غير مسجل لمجال {dom.name_ar}. المقاييس المتاحة: {', '.join(dom.measures)}.",
                missing="مقياس غير مسجل")
            self.trial_log.append((question, a.missing)); return a
        dim = _dimension(q, dom)
        if dim is not None and dim not in dom.dimensions:
            a = CompanyAnswer(question, dom_key, False,
                f"امتناع: البعد غير مسجل لمجال {dom.name_ar}. الأبعاد المتاحة: {', '.join(dom.dimensions)}.",
                missing="بعد غير مسجل")
            self.trial_log.append((question, a.missing)); return a
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True); con.row_factory = sqlite3.Row
        try:
            ref = self._ref(con)
            period_label, start, end = _period(q, ref)
            bid = _branch(q)
            frag, definition = dom.measures[meas]
            # Special registered variants
            extra = ""
            if dom_key == "accounting" and "مدفوع" in q:
                extra = " AND status = 'paid'"; definition = "مجموع مبالغ الفواتير المدفوعة"
            elif dom_key == "accounting" and "متاخر" in q:
                extra = " AND status = 'overdue'"; definition = "عدد الفواتير المتأخرة"
                if meas == "sum": frag, definition = "SUM(amount_egp)", "مجموع مبالغ الفواتير المتأخرة"
            elif dom_key == "cars" and "متاح" in q:
                extra = " AND status = 'available'"
            else:
                extra = SPECIAL.get((dom_key, meas), "")
            params = {"start": start, "end": end}
            where = ""
            if dom.date_col:
                where = f" WHERE {dom.date_col} BETWEEN :start AND :end"
            elif extra:
                where = " WHERE 1=1"
            if bid is not None:
                where += " AND branch_id = :branch_id"; params["branch_id"] = bid
            where += extra
            if dim:
                col = dom.dimensions[dim]
                sql = f"SELECT {col} AS d, {frag} AS v FROM {dom.table}{where} GROUP BY {col} ORDER BY v DESC"
                rows = con.execute(sql, params).fetchall()
                data = [(r["d"], round(float(r["v"]), 2) if isinstance(r["v"], float) else r["v"]) for r in rows]
                if not data:
                    return CompanyAnswer(question, dom_key, False, "امتناع: لا توجد داتا في الفترة المحددة.", missing="لا توجد داتا")
                text = f"{definition} حسب {dim} في {period_label} ({start} إلى {end}): {data}. المصدر: {dom.table}."
                return CompanyAnswer(question, dom_key, True, text, None, data, definition, (dom.table,))
            sql = f"SELECT {frag} AS v FROM {dom.table}{where}"
            row = con.execute(sql, params).fetchone()
            v = row["v"]
            if v is None:
                return CompanyAnswer(question, dom_key, False, "امتناع: لا توجد داتا في الفترة المحددة.", missing="لا توجد داتا")
            if isinstance(v, float): v = round(v, 2)
            branch_text = f" للفرع {bid}" if bid else ""
            text = f"{definition}{branch_text} في {period_label} ({start} إلى {end}): {v}. المصدر: {dom.table}."
            return CompanyAnswer(question, dom_key, True, text, v, None, definition, (dom.table,))
        finally:
            con.close()

if __name__ == "__main__":
    eng = CompanyEngine()
    for q in [
        "إجمالي إيراد المبيعات في كل فترة الداتا التجريبية",
        "عدد كروت الصيانة حسب نوع الخدمة في كل فترة الداتا التجريبية",
        "عدد العملاء المحتملين حسب المصدر في كل فترة الداتا التجريبية",
        "إجمالي الفواتير المدفوعة في كل فترة الداتا التجريبية",
        "عدد السيارات المتاحة في المخزون حسب الموديل في كل فترة الداتا التجريبية",
        "متوسط رضا العملاء في كل فترة الداتا التجريبية",
        "ما هي مرتبات الموظفين؟",
        "إجمالي مبيعات الموارد البشرية في كل فترة الداتا التجريبية",
    ]:
        a = eng.ask(q)
        print(f"{'CONFIRMED' if a.confirmed else 'ABSTAIN'} | {a.domain} | {a.text}")
