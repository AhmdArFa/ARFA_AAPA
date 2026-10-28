"""Unified agent: core metrics + company domains + evidence, one entry point.

Order, fail closed:
1. Sensitive check: salary, phone, password, national ID -> abstain, always.
2. Evidence tools: profit, warehouse, specific employee (exact demo name).
3. Core agent: the 11 governed 4S metrics, via agent.ask, with company.db
   if it exists, otherwise demo.db.
4. Company domains: CRM, accounting, cars, and breakdowns, via domains.CompanyEngine.
5. Otherwise: abstain, list available tools and domains, log to trial log.
The database calculates in every confirmed path. The agent never writes SQL
from the question, never calculates a number itself, and never guesses.
"""
from dataclasses import dataclass
from pathlib import Path

from .agent import ask as core_ask, _normalize as _norm_ar
from .domains import CompanyEngine
from .evidence import EvidenceEngine
from .tools import TOOLS

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPANY_DB = REPO_ROOT / "data" / "company.db"
DEMO_DB = REPO_ROOT / "data" / "demo.db"

@dataclass
class UnifiedAnswer:
    question: str
    tool: str | None
    domain: str | None
    confirmed: bool
    text: str
    value: object = None
    evidence: dict = None
    missing: str = ""

class UnifiedAgent:
    SENSITIVE = ["مرتب", "راتب", "هاتف", "تليفون", "رقم قومي", "كلمه سر", "باسورد",
                 "salary", "phone", "password", "national_id"]
    def __init__(self, db_path: Path | None = None):
        if db_path:
            self.db_path = Path(db_path)
        elif COMPANY_DB.exists():
            self.db_path = COMPANY_DB
        else:
            self.db_path = DEMO_DB
        self.trial_log: list = []
        self._domains = None
        self._evidence = None
    def _get_domains(self):
        if self._domains is None:
            try:
                self._domains = CompanyEngine(self.db_path)
            except Exception:
                self._domains = None
        return self._domains
    def _get_evidence(self):
        if self._evidence is None:
            try:
                self._evidence = EvidenceEngine(self.db_path)
            except Exception:
                self._evidence = None
        return self._evidence
    def available_tools(self):
        return [t.name for t in TOOLS]
    INJECTION_MARKERS = [";", "--", "/*", "*/", "drop", "insert", "delete", "union", "pragma", "attach", "select "]
    OUT_OF_SCOPE = ["عقار", "real estate", "اسهم", "بورصه", "ذهب", "عملات"]
    def ask(self, question: str) -> UnifiedAnswer:
        q = _norm_ar(question)
        low = question.lower()
        if any(m in low for m in self.INJECTION_MARKERS):
            a = UnifiedAnswer(question, None, None, False,
                "امتناع: السؤال يحتوي على صيغة SQL غير مسموحة، ولا يتم تنفيذ أي جزء منه.",
                missing="صيغة SQL في السؤال")
            self.trial_log.append((question, a.missing)); return a
        if any(w in q for w in self.OUT_OF_SCOPE):
            a = UnifiedAnswer(question, None, None, False,
                "امتناع: هذا المجال غير مسجل في شركات الديمو، والمجالات المتاحة هي المبيعات والصيانة وقطع الغيار والاستبيانات وCRM والمحاسبة ومخزون السيارات.",
                missing="مجال خارج الشركة")
            self.trial_log.append((question, a.missing)); return a
        if any(w in q for w in self.SENSITIVE):
            a = UnifiedAnswer(question, None, None, False,
                "امتناع: المرتبات والهواتف والبيانات الشخصية غير متاحة، حتى للمدير، بدون مقياس معتمد منفصل.",
                missing="بيانات حساسة")
            self.trial_log.append((question, a.missing)); return a
        # Evidence first, because profit/warehouse/employee are specific tools
        ev_engine = self._get_evidence()
        if ev_engine is not None and any(w in q for w in ["ربح", "ارباح", "profit", "مخزن", "مخزون", "warehouse", "stock"]) or (ev_engine is not None and any(name in question for name in ["مندوب مبيعات", "فني صيانة", "مستشار خدمة", "محاسب", "مسؤول قطع"])):
            try:
                a = ev_engine.ask(question)
                if a.confirmed:
                    return UnifiedAnswer(question, "company_profit" if a.kind == "profit" else "warehouse_stock" if a.kind == "warehouse" else "employee_performance", a.kind, True, a.text, a.value, a.evidence)
                # If evidence abstains for a specific reason other than "not matching", keep it
                if a.kind is not None:
                    return UnifiedAnswer(question, None, a.kind, False, a.text, None, a.evidence, a.missing)
            except Exception:
                pass
        # Core metrics, via the original agent, with the same db
        try:
            core = core_ask(question, self.db_path if self.db_path.exists() else None)
            if core.confirmed:
                return UnifiedAnswer(question, core.metric_key, None, True, core.text, core.value,
                                     {"definition": core.definition, "source_tables": core.source_tables, "period": core.period_label})
        except Exception:
            pass
        # Company domains fallback
        dom_engine = self._get_domains()
        if dom_engine is not None:
            try:
                d = dom_engine.ask(question)
                if d.confirmed:
                    return UnifiedAnswer(question, d.domain, d.domain, True, d.text, d.value,
                                         {"definition": d.definition, "source_tables": d.source_tables})
                # Keep domain abstention only if it is a domain question; otherwise fall through to final abstain
                if d.domain is not None:
                    self.trial_log.append((question, d.missing))
                    return UnifiedAnswer(question, None, d.domain, False, d.text, None, None, d.missing)
            except Exception:
                pass
        tools_list = ", ".join(self.available_tools())
        a = UnifiedAnswer(question, None, None, False,
            f"امتناع: السؤال غير مطابق لأداة معتمدة. الأدوات المتاحة: {tools_list}.",
            missing="لا توجد أداة معتمدة لهذا السؤال")
        self.trial_log.append((question, a.missing)); return a

if __name__ == "__main__":
    agent = UnifiedAgent()
    for q in [
        "إجمالي الإيراد في آخر 30 يوم",
        "إجمالي إيراد المبيعات في كل فترة الداتا التجريبية",
        "عدد العملاء المحتملين حسب المصدر في كل فترة الداتا التجريبية",
        "ما هي أرباح الشركة في كل فترة الداتا التجريبية؟",
        "ما هو مخزون البطارية في المخازن؟",
        "كم كارت صيانة قفل فني صيانة 1؟",
        "ما هو مرتب فني صيانة 1؟",
    ]:
        a = agent.ask(q)
        print(f"{'CONFIRMED' if a.confirmed else 'ABSTAIN'} | {a.tool} | {a.text}")
