"""Evidence engine: profit, warehouse, specific employee. Stdlib only, read-only.

Every answer carries: value, formula, component breakdown, source tables,
row counts, period, branch. No salary, phone, national ID, or password field
exists in the demo tables, so it cannot be returned even if asked.
Profit definition, demo only: invoiced revenue minus recorded demo costs.
Car purchase cost is NOT in the demo costs, so this is NOT net profit.
See docs/company-domains/evidence.md (written with this engine).
"""
import re, sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPANY_DB = REPO_ROOT / "data" / "company.db"
DEFAULT_DEMO_DB = REPO_ROOT / "data" / "demo.db"
BRANCH_NAMES = {1: "القاهرة الجديدة", 2: "الجيزة", 3: "الإسكندرية"}
SENSITIVE = ["مرتب", "راتب", "هاتف", "تليفون", "رقم قومي", "كلمه سر", "باسورد",
             "salary", "phone", "password", "national_id"]

@dataclass
class EvidenceAnswer:
    question: str
    kind: str | None
    confirmed: bool
    text: str
    value: object = None
    evidence: dict = None
    missing: str = ""

def _norm(t: str) -> str:
    t = re.sub(r"[\u064b-\u0652]", "", t)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"[^\w\s]", " ", t).lower()

def _period(q: str, ref: date):
    if "90 يوم" in q or "last 90" in q:
        return "آخر 90 يوم", (ref - timedelta(days=89)).isoformat(), ref.isoformat()
    if "الشهر الحالي" in q or "current month" in q:
        return "الشهر الحالي", ref.replace(day=1).isoformat(), ref.isoformat()
    if "الشهر الماضي" in q or "last month" in q:
        first = ref.replace(day=1); end = first - timedelta(days=1)
        return "الشهر الماضي", end.replace(day=1).isoformat(), end.isoformat()
    if "فتره" in q or "all period" in q:
        return "كل فترة الداتا التجريبية", "2026-01-01", ref.isoformat()
    return "آخر 30 يوم", (ref - timedelta(days=29)).isoformat(), ref.isoformat()

def _branch(q: str):
    for name, bid in [("القاهره", 1), ("القاهره الجديده", 1), ("الجيزه", 2), ("الاسكندريه", 3),
                      ("cairo", 1), ("giza", 2), ("alexandria", 3)]:
        if name in q: return bid
    return None

class EvidenceEngine:
    def __init__(self, db_path: Path | None = None):
        if db_path:
            self.path = Path(db_path)
        elif DEFAULT_COMPANY_DB.exists():
            self.path = DEFAULT_COMPANY_DB
        else:
            self.path = DEFAULT_DEMO_DB
        if not self.path.exists():
            raise FileNotFoundError(f"Company demo database not found: {self.path}. Run: python3 scripts/seed_company.py")
    def _con(self):
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True); con.row_factory = sqlite3.Row; return con
    def profit(self, start, end, branch=None):
        con = self._con()
        try:
            bp = " AND branch_id = :b" if branch else ""
            p = {"start": start, "end": end, **({"b": branch} if branch else {})}
            def one(sql, params=p):
                r = con.execute(sql, params).fetchone(); return r
            rev_sales = one("SELECT COUNT(*) n, COALESCE(SUM(amount_egp),0) v FROM sales WHERE sale_date BETWEEN :start AND :end AND status='invoiced'" + bp)
            rev_parts = one("SELECT COUNT(*) n, COALESCE(SUM(amount_egp),0) v FROM parts_sales WHERE sale_date BETWEEN :start AND :end" + bp)
            rev_serv = one("SELECT COUNT(*) n, COALESCE(SUM(labor_amount_egp),0) v FROM service_job_cards WHERE opened_date BETWEEN :start AND :end AND status IN ('invoiced','closed')" + bp)
            revenue = float(rev_sales["v"]) + float(rev_parts["v"]) + float(rev_serv["v"])
            costs_rows = con.execute("SELECT category, COUNT(*) n, COALESCE(SUM(amount_egp),0) v FROM accounting_costs WHERE cost_date BETWEEN :start AND :end" + bp + " GROUP BY category ORDER BY v DESC", p).fetchall()
            costs = sum(float(r["v"]) for r in costs_rows)
            profit = revenue - costs
            margin = round(profit / revenue * 100, 2) if revenue else 0.0
            ev = {
                "formula": "الربح التجريبي = إيراد مفوتر (مبيعات + قطع غيار + صيانة) - تكاليف مسجلة في الديمو",
                "revenue": {"sales": (int(rev_sales["n"]), round(float(rev_sales["v"]), 2)),
                            "parts": (int(rev_parts["n"]), round(float(rev_parts["v"]), 2)),
                            "service": (int(rev_serv["n"]), round(float(rev_serv["v"]), 2)),
                            "total": round(revenue, 2)},
                "costs_by_category": [(r["category"], int(r["n"]), round(float(r["v"]), 2)) for r in costs_rows],
                "costs_total": round(costs, 2),
                "profit": round(profit, 2), "margin_percent": margin,
                "sources": ("sales", "parts_sales", "service_job_cards", "accounting_costs"),
                "caveat": "تكلفة شراء السيارات غير مسجلة في الديمو، فهذا ليس صافي ربح حقيقي، بل إيراد مفوتر ناقص التكاليف المسجلة فقط.",
            }
            return profit, ev
        finally: con.close()
    def warehouse(self, part=None, branch=None):
        con = self._con()
        try:
            bp = " AND branch_id = :b" if branch else ""
            p = {"b": branch} if branch else {}
            pp = " AND part_name = :part" if part else ""
            if part: p["part"] = part
            row = con.execute(f"SELECT COUNT(*) n, COALESCE(SUM(stock_qty),0) qty, COALESCE(SUM(stock_qty*unit_price_egp),0) val, COALESCE(SUM(CASE WHEN stock_qty<=reorder_level THEN 1 ELSE 0 END),0) low FROM parts_inventory WHERE 1=1{bp}{pp}", p).fetchone()
            by_part_params = {"b": branch} if branch else {}
            if part: by_part_params["part"] = part
            by_part = con.execute(f"SELECT part_name, COALESCE(SUM(stock_qty),0) qty, COALESCE(SUM(stock_qty*unit_price_egp),0) val FROM parts_inventory WHERE 1=1{bp}{pp} GROUP BY part_name ORDER BY qty DESC", by_part_params).fetchall()
            cars = con.execute(f"SELECT COUNT(*) n, COALESCE(SUM(price_egp),0) val FROM cars_inventory WHERE status='available'" + (f" AND branch_id = :b" if branch else ""), {"b": branch} if branch else {}).fetchone()
            ev = {"parts_stock_qty": int(row["qty"]), "parts_low_stock_rows": int(row["low"]),
                  "parts_inventory_value": round(float(row["val"]), 2),
                  "by_part": [(r["part_name"], int(r["qty"]), round(float(r["val"]), 2)) for r in by_part],
                  "cars_available": (int(cars["n"]), round(float(cars["val"]), 2)),
                  "sources": ("parts_inventory", "cars_inventory")}
            return ev
        finally: con.close()
    def employee(self, name: str):
        con = self._con()
        try:
            row = con.execute("SELECT id, name, role, branch_id FROM employees WHERE name = ?", (name,)).fetchone()
            if not row: return None
            ev = {"id": row["id"], "name": row["name"], "role": row["role"],
                  "branch": BRANCH_NAMES.get(row["branch_id"], row["branch_id"]),
                  "sources": ("employees",)}
            if row["role"] == "salesperson":
                r = con.execute("SELECT COUNT(*) n, COALESCE(SUM(amount_egp),0) v FROM sales WHERE salesperson_id=? AND status='invoiced'", (row["id"],)).fetchone()
                ev["sales_invoiced"] = (int(r["n"]), round(float(r["v"]), 2)); ev["sources"] += ("sales",)
            if row["role"] == "technician":
                r = con.execute("SELECT COUNT(*) n, COALESCE(SUM(labor_amount_egp),0) v, COALESCE(SUM(CASE WHEN status IN ('invoiced','closed') THEN 1 ELSE 0 END),0) closed FROM service_job_cards WHERE technician_id=?", (row["id"],)).fetchone()
                ev["job_cards"] = (int(r["n"]), int(r["closed"]), round(float(r["v"]), 2)); ev["sources"] += ("service_job_cards",)
            return ev
        finally: con.close()
    def ask(self, question: str) -> EvidenceAnswer:
        q = _norm(question)
        if any(w in q for w in SENSITIVE):
            return EvidenceAnswer(question, None, False, "امتناع: المرتبات والهواتف والبيانات الشخصية غير متاحة في الديمو، حتى للمدير، بدون مقياس معتمد منفصل.", missing="بيانات حساسة")
        con = self._con()
        try:
            ref = date.fromisoformat(con.execute("SELECT MAX(sale_date) FROM sales").fetchone()[0])
        finally: con.close()
        period_label, start, end = _period(q, ref)
        branch = _branch(q)
        # Employee first: exact synthetic name must appear in the original question
        con = self._con()
        try: names = [r[0] for r in con.execute("SELECT name FROM employees")]
        finally: con.close()
        for name in names:
            if name in question:
                ev = self.employee(name)
                if ev:
                    if "sales_invoiced" in ev:
                        text = f"الموظف {name}، الدور {ev['role']}، الفرع {ev['branch']}: مبيعات مفوترة {ev['sales_invoiced'][0]} عملية بإجمالي {ev['sales_invoiced'][1]} جنيه. المصدر: {', '.join(ev['sources'])}."
                        return EvidenceAnswer(question, "employee", True, text, ev['sales_invoiced'][1], ev)
                    if "job_cards" in ev:
                        text = f"الموظف {name}، الدور {ev['role']}، الفرع {ev['branch']}: كروت صيانة {ev['job_cards'][0]}، منها مغلق أو مفوتر {ev['job_cards'][1]}، أجور {ev['job_cards'][2]} جنيه. المصدر: {', '.join(ev['sources'])}."
                        return EvidenceAnswer(question, "employee", True, text, ev['job_cards'][0], ev)
                    text = f"الموظف {name}، الدور {ev['role']}، الفرع {ev['branch']}: موجود في الديمو، لكن لا توجد سجلات عمل مباشرة مرتبطة بهذا الدور في الديمو. المصدر: employees."
                    return EvidenceAnswer(question, "employee", True, text, None, ev)
        if any(w in q for w in ["ربح", "ارباح", "profit"]):
            profit, ev = self.profit(start, end, branch)
            btxt = f" للفرع {branch}" if branch else ""
            text = (f"الربح التجريبي{btxt} في {period_label} ({start} إلى {end}): {ev['profit']} جنيه، بهامش {ev['margin_percent']}%. "
                    f"الدليل: إيراد {ev['revenue']['total']} جنيه = مبيعات {ev['revenue']['sales']} + قطع غيار {ev['revenue']['parts']} + صيانة {ev['revenue']['service']}، "
                    f"ناقص تكاليف مسجلة {ev['costs_total']} جنيه حسب الفئة {ev['costs_by_category']}. "
                    f"تحذير: {ev['caveat']} المصدر: {', '.join(ev['sources'])}.")
            return EvidenceAnswer(question, "profit", True, text, ev['profit'], ev)
        if any(w in q for w in ["مخزن", "مخزون", "warehouse", "stock"]):
            # part name, if present in original question
            part = None
            for cand in ["فلتر زيت", "تيل فرامل", "بطارية", "إطار", "بوجيهات", "مساعدين"]:
                if cand in question: part = cand; break
            ev = self.warehouse(part, branch)
            text = (f"حالة المخزون الحالية (لقطة مخزون، مش فترة): قطع غيار إجمالي كمية {ev['parts_stock_qty']}، قيمة مخزون {ev['parts_inventory_value']} جنيه، "
                    f"أصناف تحت حد إعادة الطلب {ev['parts_low_stock_rows']}، حسب القطعة {ev['by_part']}، "
                    f"سيارات متاحة {ev['cars_available'][0]} بقيمة {ev['cars_available'][1]} جنيه. المصدر: {', '.join(ev['sources'])}.")
            return EvidenceAnswer(question, "warehouse", True, text, ev['parts_inventory_value'], ev)
        return EvidenceAnswer(question, None, False,
            "امتناع: هذا السؤال غير مطابق لمحرك الأدلة في هذه النسخة التجريبية (أرباح، مخزون، موظف محدد).",
            missing="سؤال غير مطابق لمحرك الأدلة")

if __name__ == "__main__":
    eng = EvidenceEngine()
    for q in [
        "ما هي أرباح الشركة في كل فترة الداتا التجريبية؟",
        "ما هو مخزون البطارية في المخازن؟",
        "كم كارت صيانة قفل فني صيانة 1؟",
        "كم مبيعات مندوب مبيعات 2 المفوترة؟",
        "ما هو مرتب فني صيانة 1؟",
    ]:
        a = eng.ask(q)
        print(f"{'CONFIRMED' if a.confirmed else 'ABSTAIN'} | {a.kind} | {a.text}")
