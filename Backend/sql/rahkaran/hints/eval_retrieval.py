"""Offline retrieval evaluation (no embedding API needed): ranks the hint chunks for each evaluation question with a lexical scorer
(BM25 over word tokens + Persian character 4-grams) and reports how often the views a correct answer needs are covered by the top-k chunks.

Leave-one-out: for the seed questions of examples/questions.py the question's own example chunk is excluded.
An embedding retriever (BGE-M3) is expected to do at least as well; this is the lower bound and a regression test for the hints.
Usage: python eval_retrieval.py [k=6]
"""
import json, math, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "examples"))
from eval_set import E
from questions import Q

K = int(sys.argv[1]) if len(sys.argv) > 1 else 6
chunks = [json.loads(l) for l in open(os.path.join(HERE, "out", "hints.jsonl"), encoding="utf-8")]

def norm(t):
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه").replace("‌", " ").replace("‌", " ")
    t = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), t)
    t = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), t)
    return re.sub(r"[^\w\s]", " ", t.lower())

STOP = set("از در به با که را این آن یا و تا برای است شد شده هست بود می چه چقدر چند کدام کدوم الان امسال ما ایم شرکت میشه هستن داریم کن".split())

def toks(t):
    words = [w for w in norm(t).split() if w not in STOP and len(w) > 1]
    grams = []
    for w in words:
        w2 = f"#{w}#"
        grams += [w2[i:i + 4] for i in range(max(1, len(w2) - 3))] if len(w) >= 3 else []
    return words + grams

def build(strip_sample_questions):
    texts = [re.sub(r"\nنمونه پرسش‌ها:.*", "", c["text"]) if strip_sample_questions else c["text"] for c in chunks]
    d = [toks(c["title"] + " " + " ".join(c.get("keywords", [])) + " " + t) for c, t in zip(chunks, texts)]
    # boost title/keywords by repeating them
    return [x + toks(c["title"] + " " + " ".join(c.get("keywords", []))) * 2 for x, c in zip(d, chunks)]
STRIP = False
def index(strip):
    global docs, N, avgdl, df, tf
    docs = build(strip); N = len(docs); avgdl = sum(map(len, docs)) / N
    df = collections.Counter(t for d in docs for t in set(d)); tf = [collections.Counter(d) for d in docs]
index(False)
def bm25(q, i, k1=1.4, b=0.6):
    s = 0.0
    for t in set(q):
        if t not in tf[i]: continue
        idf = math.log(1 + (N - df[t] + .5) / (df[t] + .5))
        f = tf[i][t]
        s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(docs[i]) / avgdl))
    return s

def rank(question, exclude=None):
    q = toks(question)
    sc = [(bm25(q, i), i) for i in range(N) if chunks[i]["id"] != exclude]
    sc.sort(reverse=True)
    return [chunks[i] for _, i in sc[:K]]

def evaluate(items, label, leave_one_out):
    full = partial = 0; misses = []
    for item in items:
        if leave_one_out:
            idx, question, expected = item
            top = rank(question, exclude=f"example:{idx:03d}")
        else:
            question, expected = item
            top = rank(question)
        got = {v for c in top for v in c["views"]}
        # a question is routed if at least ONE acceptable view is covered (alternatives are listed); strict = all expected covered
        hit_any = any(v in got for v in expected)
        hit_all = all(v in got for v in expected)
        full += hit_all if leave_one_out else hit_any
        partial += hit_any
        if not (hit_all if leave_one_out else hit_any):
            misses.append((question, expected, [c["id"] for c in top]))
    n = len(items)
    print(f"{label}: {full}/{n} = {100 * full / n:.0f}%  (at least one needed view in top-{K}: {partial}/{n})")
    return misses

seed = []
for i, (group, question, sql) in enumerate(Q, 1):
    seed.append((i, question, sorted(set(re.findall(r"ai\.(\w+)", sql)))))
index(True)   # seed run must not see the sample questions embedded in the view chunks (leakage)
m1 = evaluate(seed, "seed questions (leave-one-out, no leakage, ALL needed views covered)", True)
index(False)
m2 = evaluate(E, "paraphrased questions (any acceptable view covered)", False)
for q, exp, top in m2:
    print("  MISS:", q, "| expected:", exp, "| top:", top[:4])
for _, q, exp in [(0, a, b) for a, b, c in [(x[1], x[2], 0) for x in seed[:0]]]:
    pass
if "-v" in sys.argv:
    for q, exp, top in m1[:10]:
        print("  seed miss:", q, exp, top[:4])
