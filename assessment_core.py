"""Locked question/rubric definitions and evidence-based grading.

Only public_view() may be sent before submission. Student input never supplies
the answer key, rubric, expected output, or grading status.
"""
from __future__ import annotations

import re
import unicodedata
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Language = Literal["python", "java", "c", "cpp"]
QuestionKind = Literal["mcq", "theory", "code"]
Verdict = Literal["CHÍNH XÁC", "CHƯA CHÍNH XÁC", "ĐÚNG MỘT PHẦN"]


class AssessmentUnavailable(ValueError):
    """Insufficient or inconsistent evidence; do not turn this into a zero."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TestCase(FrozenModel):
    id: str = Field(min_length=1, max_length=40)
    input: str = Field(max_length=65536)
    expected_output: str = Field(max_length=65536)


class Criterion(FrozenModel):
    id: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=1200)
    weight: int = Field(ge=1, le=10)
    aliases: tuple[str, ...] = Field(default=(), max_length=20)
    contradiction_patterns: tuple[str, ...] = Field(default=(), max_length=10)


class GroundTruth(FrozenModel):
    dap_an_dung: str = Field(min_length=1, max_length=60000)
    tu_khoa_cot_loi: tuple[Criterion, ...] = Field(default=(), max_length=20)
    test_cases: tuple[TestCase, ...] = Field(default=(), max_length=10)
    giai_thich_chuan: str = Field(min_length=1, max_length=8000)


class Option(FrozenModel):
    label: Literal["A", "B", "C", "D"]
    text: str = Field(min_length=1, max_length=2000)


class QuestionSpec(FrozenModel):
    id: str = Field(min_length=1, max_length=80)
    language: Language
    kind: QuestionKind
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=6000)
    options: tuple[Option, ...] = ()
    starter_code: str = Field(default="", max_length=60000)
    source_urls: tuple[str, ...] = Field(min_length=1, max_length=5)
    standard_version: str = Field(min_length=1, max_length=300)
    ground_truth: GroundTruth

    @model_validator(mode="after")
    def validate_definition(self):
        if self.kind == "mcq":
            if {option.label for option in self.options} != set("ABCD") or len(self.options) != 4:
                raise ValueError("Trắc nghiệm phải có đúng bốn lựa chọn A/B/C/D.")
            if self.ground_truth.dap_an_dung not in set("ABCD"):
                raise ValueError("Đáp án trắc nghiệm không hợp lệ.")
        elif self.options:
            raise ValueError("Chỉ câu hỏi trắc nghiệm có các lựa chọn.")
        criteria = self.ground_truth.tu_khoa_cot_loi
        if len({criterion.id for criterion in criteria}) != len(criteria):
            raise ValueError("Mã tiêu chí bị trùng.")
        if self.kind == "theory" and (not criteria or sum(c.weight for c in criteria) != 10):
            raise ValueError("Thang tiêu chí tự luận phải có tổng trọng số bằng 10.")
        tests = self.ground_truth.test_cases
        if self.kind == "code" and len(tests) < 3:
            raise ValueError("Câu hỏi code phải có ít nhất ba test chuẩn.")
        if self.kind != "code" and tests:
            raise ValueError("Test chạy chỉ áp dụng cho câu hỏi code.")
        if len({case.id for case in tests}) != len(tests):
            raise ValueError("Mã test bị trùng.")
        return self

    def public_view(self, question_id: str) -> dict:
        """Explicit allowlist: no answer/rubric/test can leak through serialization."""
        return {
            "question_id": question_id,
            "kind": self.kind,
            "language": self.language,
            "title": self.title,
            "prompt": self.prompt,
            "options": {option.label: option.text for option in self.options},
            "starter_code": self.starter_code,
            "source_urls": list(self.source_urls),
            "standard_version": self.standard_version,
        }


class AssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trang_thai: Verdict
    diem_so: float = Field(ge=0, le=10)
    diem_dung: list[str] = Field(max_length=40)
    diem_sai: list[str] = Field(max_length=40)
    dap_an_chuan: str = Field(min_length=1, max_length=60000)
    giai_thich_chuan: str = Field(min_length=1, max_length=8000)
    phuong_phap: str = Field(min_length=1, max_length=200)
    gioi_han: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_score(self):
        if self.trang_thai != verdict_for_score(self.diem_so):
            raise ValueError("Trạng thái và điểm số không nhất quán.")
        return self


class RubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    criterion_id: str = Field(min_length=1, max_length=40)
    decision: Literal["met", "not_met", "uncertain"]
    evidence: str = Field(max_length=4000)
    explanation: str = Field(min_length=1, max_length=600)


class RubricJudgment(BaseModel):
    """Criterion evidence only; hidden reasoning is neither requested nor returned."""
    model_config = ConfigDict(extra="forbid", strict=True)
    question_id: str = Field(min_length=1, max_length=80)
    criteria: list[RubricItem] = Field(min_length=1, max_length=20)


def verdict_for_score(score: float) -> Verdict:
    if score == 10:
        return "CHÍNH XÁC"
    if score == 0:
        return "CHƯA CHÍNH XÁC"
    return "ĐÚNG MỘT PHẦN"


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def _folded(text: str) -> str:
    value = unicodedata.normalize("NFD", text.casefold())
    return " ".join("".join(char for char in value if not unicodedata.combining(char)).replace("đ", "d").split())


def _contains_alias(text: str, alias: str) -> bool:
    text, alias = _folded(text), _folded(alias)
    if not alias:
        return False
    pattern = re.escape(alias)
    if alias[0].isalnum() or alias[0] == "_":
        pattern = r"(?<!\w)" + pattern
    if alias[-1].isalnum() or alias[-1] == "_":
        pattern += r"(?!\w)"
    return bool(re.search(pattern, text))


def _result(spec, score, correct, incorrect, method, limitation):
    score = round(float(score), 2)
    return AssessmentResult(
        trang_thai=verdict_for_score(score), diem_so=score,
        diem_dung=correct, diem_sai=incorrect,
        dap_an_chuan=spec.ground_truth.dap_an_dung,
        giai_thich_chuan=spec.ground_truth.giai_thich_chuan,
        phuong_phap=method, gioi_han=limitation,
    )


def grade_mcq(spec: QuestionSpec, answer: str) -> AssessmentResult:
    if spec.kind != "mcq":
        raise ValueError("Đây không phải câu hỏi trắc nghiệm.")
    choice = answer.strip().upper()
    if len(choice) != 1 or choice not in "ABCD":
        raise ValueError("Chỉ gửi một lựa chọn A, B, C hoặc D.")
    passed = choice == spec.ground_truth.dap_an_dung
    option = next(item.text for item in spec.options if item.label == spec.ground_truth.dap_an_dung)
    result = _result(
        spec, 10 if passed else 0,
        [f"Bạn chọn đúng phương án {choice}."] if passed else [],
        [] if passed else [f"Phương án {choice} chưa đúng; đáp án đã khóa là {spec.ground_truth.dap_an_dung}."],
        "So sánh lựa chọn với đáp án đã khóa bằng Python",
        "Điểm xác định bằng đáp án cố định; không gọi AI để quyết định lại lựa chọn.",
    )
    result.dap_an_chuan = f"{spec.ground_truth.dap_an_dung}. {option}"
    return result


def exact_theory_match(spec: QuestionSpec, answer: str) -> AssessmentResult | None:
    if spec.kind != "theory":
        raise ValueError("Đây không phải câu hỏi tự luận.")
    if _normalized(answer) != _normalized(spec.ground_truth.dap_an_dung):
        return None
    return _result(
        spec, 10,
        [criterion.description for criterion in spec.ground_truth.tu_khoa_cot_loi], [],
        "Đối chiếu toàn bộ câu trả lời chuẩn đã khóa",
        "Chỉ chuẩn hóa chữ hoa/thường, Unicode và khoảng trắng; không chấm bằng sự xuất hiện từ khóa.",
    )


def grade_theory(spec: QuestionSpec, answer: str, judgment: RubricJudgment) -> AssessmentResult:
    exact = exact_theory_match(spec, answer)
    if exact:
        return exact
    criteria = {criterion.id: criterion for criterion in spec.ground_truth.tu_khoa_cot_loi}
    if judgment.question_id != spec.id:
        raise AssessmentUnavailable("Kết quả đối chiếu không thuộc câu hỏi đã lưu. Chưa kết luận Đúng/Sai.")
    item_ids = [item.criterion_id for item in judgment.criteria]
    if len(item_ids) != len(set(item_ids)) or set(item_ids) != set(criteria):
        raise AssessmentUnavailable("AI chưa đối chiếu đủ và đúng các tiêu chí đã khóa. Chưa chấm điểm.")
    correct, incorrect = [], []
    score = 0
    for item in judgment.criteria:
        criterion = criteria[item.criterion_id]
        quote = item.evidence.strip()
        if item.decision == "uncertain":
            raise AssessmentUnavailable("Còn tiêu chí chưa đủ căn cứ đánh giá. Hãy trả lời rõ hơn hoặc nhờ giảng viên đối chiếu.")
        if quote and quote not in answer:
            raise AssessmentUnavailable("Phần dẫn chứng của AI không có trong câu trả lời sinh viên. Chưa chấm điểm.")
        if item.decision == "met":
            if not quote:
                raise AssessmentUnavailable("AI chưa dẫn chứng phần trả lời đáp ứng tiêu chí. Chưa chấm điểm.")
            if criterion.aliases and not any(_contains_alias(quote, alias) for alias in criterion.aliases):
                raise AssessmentUnavailable("Dẫn chứng chưa đối chiếu được với tiêu chí. Chưa chấm điểm.")
            if any(re.search(pattern, _folded(answer)) for pattern in criterion.contradiction_patterns):
                raise AssessmentUnavailable("Câu trả lời còn mệnh đề phủ định hoặc mâu thuẫn với ý được đánh giá đúng. Chưa chấm điểm tự động.")
            score += criterion.weight
            correct.append(f"{criterion.description} — Dẫn chứng: “{quote}”")
        else:
            incorrect.append(f"Chưa đáp ứng: {criterion.description} — {item.explanation}")
    return _result(
        spec, score, correct, incorrect,
        "Đối chiếu AI theo tiêu chí khóa; Backend kiểm tra trích dẫn và tính điểm",
        "Tự luận dùng đối chiếu ngữ nghĩa có hỗ trợ AI, có thể cần giảng viên rà soát; không bảo đảm chính xác tuyệt đối.",
    )


def grade_code(spec: QuestionSpec, evidence: dict) -> AssessmentResult:
    if spec.kind != "code":
        raise ValueError("Đây không phải câu hỏi viết code.")
    if evidence.get("available") is not True:
        raise AssessmentUnavailable(evidence.get("reason") or "Chưa có môi trường kiểm chứng mã an toàn. Chưa chấm điểm.")
    if evidence.get("compile_ok") is False:
        errors = evidence.get("errors") or []
        if not errors:
            raise AssessmentUnavailable("Không có thông báo kiểm tra cú pháp/biên dịch để đối chiếu. Chưa chấm điểm.")
        details = [f"Dòng {item['line']}: {item['message']}" if item.get("line") else str(item.get("message", "Lỗi biên dịch")) for item in errors[:20]]
        return _result(
            spec, 0, [], details,
            "Kiểm tra cú pháp/biên dịch thực tế",
            "Chưa chạy test vì chương trình chưa vượt qua kiểm tra cú pháp/biên dịch; không suy đoán kết quả chạy.",
        )
    if evidence.get("compile_ok") is not True or evidence.get("verified") is not True:
        raise AssessmentUnavailable(evidence.get("reason") or "Chưa chạy đủ các test đã khóa. Chưa chấm điểm.")
    count = len(spec.ground_truth.test_cases)
    cases = evidence.get("cases")
    if not isinstance(cases, list) or len(cases) != count or evidence.get("total") != count:
        raise AssessmentUnavailable("Kết quả chạy không đủ số test đã khóa. Chưa chấm điểm.")
    if {case.get("index") for case in cases} != set(range(1, count + 1)):
        raise AssessmentUnavailable("Kết quả chạy có mã test trùng hoặc không hợp lệ. Chưa chấm điểm.")
    accepted_status = {"passed", "wrong_answer", "timeout", "runtime_error", "output_limit"}
    for case in cases:
        if type(case.get("passed")) is not bool or case.get("status") not in accepted_status:
            raise AssessmentUnavailable("Bằng chứng test không hợp lệ. Chưa chấm điểm.")
        if case["passed"] != (case["status"] == "passed"):
            raise AssessmentUnavailable("Trạng thái test mâu thuẫn. Chưa chấm điểm.")
    passed = sum(case["passed"] for case in cases)
    if evidence.get("passed") != passed:
        raise AssessmentUnavailable("Số test vượt qua không nhất quán. Chưa chấm điểm.")
    labels = {
        "wrong_answer": "đầu ra khác đáp án chuẩn",
        "timeout": "vượt giới hạn thời gian 3 giây",
        "runtime_error": "lỗi khi chạy",
        "output_limit": "vượt giới hạn đầu ra",
    }
    correct = [f"Vượt qua {passed}/{count} ca kiểm thử đã khóa."]
    incorrect = [f"Ca kiểm thử {case['index']}: {labels[case['status']]}." for case in cases if not case["passed"]]
    return _result(
        spec, passed * 10 / count, correct, incorrect,
        "Biên dịch và chạy test trong môi trường cách ly; điểm do Backend tính",
        "Đạt tất cả test chỉ xác nhận các ca đã chạy, không chứng minh đúng với mọi đầu vào hoặc không còn mọi lỗi.",
    )


def _options(*texts):
    return tuple(Option(label=label, text=text) for label, text in zip("ABCD", texts, strict=True))


def _criterion(id, description, weight, aliases=(), contradictions=()):
    return Criterion(id=id, description=description, weight=weight, aliases=aliases, contradiction_patterns=contradictions)


PYTHON_URL = "https://docs.python.org/3.14/tutorial/controlflow.html#defining-functions"
JAVA_URL = "https://docs.oracle.com/javase/specs/jls/se17/html/jls-5.html#jls-5.1.8"
C_URL = "https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf"
CPP_URL = "https://learn.microsoft.com/en-us/cpp/standard-library/vector-class?view=msvc-170"

_QUESTIONS = [
    QuestionSpec(
        id="python-mcq-floor-v1", language="python", kind="mcq", title="Phép chia nguyên với số âm",
        prompt="Trong Python 3, biểu thức -7 // 2 cho kết quả nào? Chọn đúng một phương án.",
        options=_options("-3", "-4", "3", "4"),
        source_urls=("https://docs.python.org/3.14/reference/expressions.html#binary-arithmetic-operations",),
        standard_version="Python 3.14, quy tắc // của số nguyên",
        ground_truth=GroundTruth(dap_an_dung="B", giai_thich_chuan="// làm tròn thương xuống âm vô cùng: -3,5 trở thành -4, không cắt về 0."),
    ),
    QuestionSpec(
        id="java-mcq-string-v1", language="java", kind="mcq", title="So sánh hai đối tượng String",
        prompt='Cho String a = new String("CNTT"); String b = new String("CNTT"); Giá trị a == b là gì?',
        options=_options("true", "false", "null", "Luôn gây lỗi biên dịch"),
        source_urls=("https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.21.3",),
        standard_version="Java SE 17",
        ground_truth=GroundTruth(dap_an_dung="B", giai_thich_chuan="Hai lệnh new tạo hai đối tượng riêng. == so sánh danh tính tham chiếu; equals mới so sánh nội dung String."),
    ),
    QuestionSpec(
        id="c-mcq-scanf-v1", language="c", kind="mcq", title="Đọc một số nguyên trong C",
        prompt="Cho int n; chọn lời gọi scanf đúng kiểu để đọc một số nguyên vào n, giả sử dữ liệu vào hợp lệ.",
        options=_options('scanf("%d", n);', 'scanf("%d", &n);', 'scanf("%f", &n);', 'scanf("%s", &n);'),
        source_urls=(C_URL,), standard_version="Bản thảo C11 N1570, §7.21.6.2",
        ground_truth=GroundTruth(dap_an_dung="B", giai_thich_chuan="%d trong scanf cần int* để ghi vào biến n; &n cung cấp địa chỉ đó. Khi dùng thực tế vẫn cần kiểm tra số lần chuyển đổi thành công."),
    ),
    QuestionSpec(
        id="cpp-mcq-empty-back-v1", language="cpp", kind="mcq", title="Truy cập cuối vector rỗng",
        prompt="Theo C++17, với std::vector<int> v; đang rỗng, điều nào đúng về việc gọi v.back()?",
        options=_options("Luôn trả số 0", "Luôn ném std::out_of_range", "Vi phạm điều kiện không rỗng; không được dựa vào kết quả", "Luôn trả nullptr"),
        source_urls=(CPP_URL,), standard_version="C++17, điều kiện trước của vector::back",
        ground_truth=GroundTruth(dap_an_dung="C", giai_thich_chuan="back() đòi hỏi vector không rỗng. Không được khẳng định lời gọi trên vector rỗng luôn trả 0 hay luôn ném ngoại lệ."),
    ),
    QuestionSpec(
        id="python-theory-return-v1", language="python", kind="theory", title="Phân biệt print và return",
        prompt="Một hàm Python chỉ gọi print(5) rồi đi hết thân, không có return: bên gọi nhận giá trị gì? print làm gì và phải thay đổi thế nào nếu muốn bên gọi nhận số 5 để tính toán tiếp?",
        source_urls=(PYTHON_URL,), standard_version="Python 3.14; hàm thông thường",
        ground_truth=GroundTruth(
            dap_an_dung="Bên gọi nhận None. print(5) ghi số 5 ra đầu ra chuẩn, không trả số 5 cho bên gọi. Muốn bên gọi nhận số 5 để tính toán tiếp, hàm cần return 5.",
            tu_khoa_cot_loi=(
                _criterion("implicit-none", "Xác định bên gọi nhận None khi hàm đi hết thân mà không return", 4, ("None",), (r"(?:khong|chua)\s+(?:tu dong\s+)?(?:tra(?:\s+ve)?|nhan)\s+none", r"(?:ben goi|ham)\s+nhan\s+0")),
                _criterion("print-output", "Phân biệt print ghi ra đầu ra chuẩn với việc trả giá trị cho bên gọi", 3, ("print", "đầu ra", "màn hình"), (r"print\s*(?:\(5\))?\s+(?:se\s+)?tra(?:\s+ve)?\s+(?:so\s+)?5",)),
                _criterion("explicit-return", "Đề xuất return 5 để bên gọi sử dụng giá trị 5", 3, ("return 5",), (r"khong\s+can\s+return",)),
            ),
            giai_thich_chuan="print xử lý hiển thị; return xử lý giá trị của lời gọi hàm. Hàm đi hết thân có kết quả None. Một hàm chỉ cần hiển thị vẫn có thể hợp lệ; ở đề này bên gọi cần dùng số 5 nên phải trả giá trị đó.",
        ),
    ),
    QuestionSpec(
        id="java-theory-unboxing-v1", language="java", kind="theory", title="Unboxing một Integer null",
        prompt="Phân tích Integer n = null; int x = n;: đoạn mã có thể vượt qua biên dịch không, lỗi gì xảy ra khi chạy và nguyên nhân là gì?",
        source_urls=(JAVA_URL,), standard_version="Java SE 17, JLS §5.1.8",
        ground_truth=GroundTruth(
            dap_an_dung="Đoạn mã có thể biên dịch. Khi chạy đến int x = n thì phát sinh NullPointerException. Phép gán cần unboxing Integer thành int nhưng tham chiếu n đang là null.",
            tu_khoa_cot_loi=(
                _criterion("compiles", "Phân biệt khả năng biên dịch với lỗi phát sinh khi chạy", 3, ("biên dịch", "compile"), (r"khong\s+(?:the\s+)?bien dich",)),
                _criterion("exception", "Xác định đúng ngoại lệ NullPointerException", 4, ("NullPointerException",), (r"khong\s+(?:gay|co|nem|phat sinh)\s+(?:ra\s+)?(?:ngoai le\s+)?nullpointerexception",)),
                _criterion("cause", "Nêu nguyên nhân unboxing một tham chiếu Integer có giá trị null", 3, ("unboxing", "null"), (r"null\s+(?:tu dong\s+)?(?:thanh|bang)\s+0",)),
            ),
            giai_thich_chuan="Java cho phép cú pháp gán có chuyển đổi unboxing, nhưng JLS quy định unboxing tham chiếu null phát sinh NullPointerException; null không tự chuyển thành số 0.",
        ),
    ),
    QuestionSpec(
        id="c-theory-io-v1", language="c", kind="theory", title="Giá trị và địa chỉ trong nhập xuất",
        prompt='Cho int n; giải thích vì sao scanf("%d", &n) cần &n, còn printf("%d", n) dùng n; cần kiểm tra gì để biết scanf đọc thành công?',
        source_urls=(C_URL,), standard_version="Bản thảo C11 N1570, §7.21.6.1–2",
        ground_truth=GroundTruth(
            dap_an_dung="scanf với %d cần địa chỉ int là &n để ghi dữ liệu vào n. printf với %d nhận giá trị int là n để in. Cần kiểm tra giá trị trả về của scanf bằng 1 để xác nhận đã đọc một số nguyên thành công.",
            tu_khoa_cot_loi=(
                _criterion("scanf-address", "Nêu scanf cần &n là địa chỉ int để ghi dữ liệu", 4, ("&n", "địa chỉ", "con trỏ"), (r"scanf.{0,40}khong\s+can\s+(?:dia chi|&n)",)),
                _criterion("printf-value", "Nêu printf nhận giá trị int, không nhận địa chỉ int với %d", 3, ("printf", "giá trị"), (r"printf.{0,35}can\s+&n",)),
                _criterion("scanf-result", "Kiểm tra scanf trả 1 khi đọc thành công một số nguyên", 3, ("1", "scanf", "trả về"), (r"scanf.{0,35}(?:thanh cong.{0,12}0|0.{0,12}thanh cong)",)),
            ),
            giai_thich_chuan="Hai hàm có hợp đồng đối số khác nhau dù cùng có %d. scanf cần vị trí đích để ghi còn printf cần giá trị để hiển thị; kết quả chuyển đổi của scanf phải được kiểm tra trước khi dùng biến.",
        ),
    ),
    QuestionSpec(
        id="cpp-theory-vector-v1", language="cpp", kind="theory", title="Lấy phần tử cuối vector an toàn",
        prompt="Trong C++17, hãy nêu điều kiện để dùng vector::back(), hậu quả nếu gọi khi vector rỗng và cách kiểm tra trước khi lấy phần tử cuối.",
        source_urls=(CPP_URL,), standard_version="C++17, vector::back và vector::empty",
        ground_truth=GroundTruth(
            dap_an_dung="back() chỉ được dùng khi vector không rỗng. Gọi back() trên vector rỗng gây hành vi không xác định, không được bảo đảm ném ngoại lệ. Kiểm tra !v.empty() trước khi dùng v.back().",
            tu_khoa_cot_loi=(
                _criterion("nonempty", "Nêu điều kiện vector không rỗng khi gọi back", 3, ("không rỗng", "non-empty", "nonempty"), (r"back.{0,30}luon\s+an toan",)),
                _criterion("undefined", "Không coi back trên vector rỗng là an toàn hoặc luôn ném ngoại lệ", 4, ("không xác định", "undefined", "không bảo đảm", "không được bảo đảm"), (r"back.{0,40}luon\s+(?:nem|tra\s+0)",)),
                _criterion("guard", "Đề xuất kiểm tra !v.empty() trước v.back()", 3, ("!v.empty()", "empty", "size() > 0", "size()>0"), (r"if\s*\(\s*v\.empty\(\)\s*\).{0,30}v\.back",)),
            ),
            giai_thich_chuan="Kiểm tra trước điều kiện không rỗng. back không có hợp đồng kiểm tra biên như at; không dùng kết quả một lần chạy để cho rằng truy cập vector rỗng là đúng.",
        ),
    ),
]

_SUM_TESTS = tuple(TestCase(id=f"sum-{i}", input=source, expected_output=expected) for i, (source, expected) in enumerate((
    ("2 3\n", "5\n"), ("-7 2\n", "-5\n"), ("0 0\n", "0\n"),
    ("1000000 -1000000\n", "0\n"), ("-1000000 -1000000\n", "-2000000\n"),
), 1))

_SUM_CODES = {
    "python": "import sys\n\ndef main():\n    a, b = map(int, sys.stdin.read().split())\n    print(a + b)\n\nif __name__ == \"__main__\":\n    main()\n",
    "c": '#include <stdio.h>\n\nint main(void) {\n    long long a, b;\n    if (scanf("%lld %lld", &a, &b) != 2) {\n        return 1;\n    }\n    printf("%lld\\n", a + b);\n    return 0;\n}\n',
    "cpp": '#include <iostream>\n\nint main() {\n    long long a, b;\n    if (!(std::cin >> a >> b)) {\n        return 1;\n    }\n    std::cout << a + b << "\\n";\n    return 0;\n}\n',
    "java": 'import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        long a = scanner.nextLong();\n        long b = scanner.nextLong();\n        System.out.println(a + b);\n    }\n}\n',
}

_SUM_STARTERS = {
    "python": "a, b = map(int, input().split())\n# In tổng a và b, không in lời nhắc.\n",
    "c": '#include <stdio.h>\n\nint main(void) {\n    long long a, b;\n    if (scanf("%lld %lld", &a, &b) != 2) return 1;\n    /* In tổng a và b, không in lời nhắc. */\n    return 0;\n}\n',
    "cpp": '#include <iostream>\n\nint main() {\n    long long a, b;\n    if (!(std::cin >> a >> b)) return 1;\n    // In tổng a và b, không in lời nhắc.\n    return 0;\n}\n',
    "java": 'import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner scanner = new Scanner(System.in);\n        long a = scanner.nextLong();\n        long b = scanner.nextLong();\n        // In tổng a và b, không in lời nhắc.\n    }\n}\n',
}

for _language in ("python", "java", "c", "cpp"):
    _QUESTIONS.append(QuestionSpec(
        id=f"{_language}-code-sum-v1", language=_language, kind="code", title="Đọc và cộng hai số nguyên",
        prompt="Viết chương trình đọc hai số nguyên a và b trên một dòng, cách nhau bởi khoảng trắng; -1.000.000 ≤ a, b ≤ 1.000.000. In duy nhất tổng a + b và một ký tự xuống dòng; không in lời nhắc nhập dữ liệu. Java dùng public class Main. Chỉ các ca kiểm thử đã chạy được dùng để tính điểm.",
        starter_code=_SUM_STARTERS[_language],
        source_urls=({"python": PYTHON_URL, "java": "https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Scanner.html", "c": C_URL, "cpp": "https://learn.microsoft.com/en-us/cpp/standard-library/iostream-programming?view=msvc-170"}[_language],),
        standard_version={"python": "Python 3.11+", "java": "Java 17", "c": "C11", "cpp": "C++17"}[_language],
        ground_truth=GroundTruth(
            dap_an_dung=_SUM_CODES[_language], test_cases=_SUM_TESTS,
            giai_thich_chuan="Đọc hai số nguyên có dấu, cộng và in tổng. Các kiểu được dùng có đủ miền giá trị cho ràng buộc đề bài. Bộ kiểm thử có số dương, số âm, số 0 và hai biên. Đạt tất cả các test này không chứng minh đúng với mọi đầu vào ngoài phạm vi đề bài.",
        ),
    ))

QUESTION_BANK = MappingProxyType({(question.language, question.kind): question for question in _QUESTIONS})


def select_question(language: Language, kind: QuestionKind) -> QuestionSpec:
    try:
        return QUESTION_BANK[(language, kind)]
    except KeyError:
        raise ValueError("Ngôn ngữ hoặc loại câu hỏi không được hỗ trợ.") from None

