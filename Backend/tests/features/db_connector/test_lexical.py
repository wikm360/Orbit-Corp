from app.features.db_connector.lexical import Bm25Index, normalize, tokens


def test_normalize():
    raw = "شركت‌های يزد، كرمان با شماره ۱۰۴۰ و ٥٠٠"
    norm = normalize(raw)
    assert "شرکت" in norm
    assert "یزد" in norm
    assert "کرمان" in norm
    assert "1040" in norm
    assert "500" in norm


def test_tokens():
    res = tokens("صورت وضعیت پیمانکاران ۱۴۰۴")
    assert "صورت" in res
    assert "وضعیت" in res
    assert "پیمانکاران" in res
    assert "1404" in res


def test_bm25_index():
    docs = [
        "حساب‌های بانکی شرکت و موجودی نقد و بانک",
        "قراردادهای پیمانکاری و صورت وضعیت تایید شده",
        "حقوق و دستمزد ماهانه کارکنان و پرسنل",
        "تراز آزمایشی چهار ستونی و مانده حساب معین",
    ]
    boosts = [
        "بانک بانک‌ها",
        "قرارداد پیمانکار پروژه",
        "حقوق دستمزد کارمند",
        "تراز معین کل",
    ]
    idx = Bm25Index(docs, boosts)

    top_bank = idx.top("موجودی حساب بانکی چقدر است", 2)
    assert top_bank[0] == 0

    top_contract = idx.top("صورت وضعیت‌های قراردادها", 2)
    assert top_contract[0] == 1

    top_payroll = idx.top("فیش حقوق دستمزد پرسنل", 2)
    assert top_payroll[0] == 2

