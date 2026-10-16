import re
from pathlib import Path
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

FALLBACK = "I couldn’t confidently match that question. Try a specific topic such as course registration, fees or transcripts, or contact your institution’s support office for personal or complex issues."


class ChatbotEngine:
    def __init__(self, kb_path=None):
        self.path = Path(kb_path or Path(__file__).with_name("knowledge_base.json"))
        self.load(json.loads(self.path.read_text()))

    def load(self, entries):
        self.entries = entries
        documents, self.owners = [], []
        for index, entry in enumerate(entries):
            for example in entry["examples"] + [entry["title"]]:
                documents.append(self.preprocess_text(example))
                self.owners.append(index)
        self.words = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words=sorted(
                ENGLISH_STOP_WORDS
                | {
                    "student",
                    "students",
                    "need",
                    "want",
                    "send",
                    "help",
                    "information",
                    "apply",
                    "application",
                    "online",
                    "office",
                    "general",
                    "support",
                    "personal",
                }
            ),
        )
        self.chars = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
        self.word_matrix = self.words.fit_transform(documents)
        self.char_matrix = self.chars.fit_transform(documents)

    @staticmethod
    def preprocess_text(text):
        text = re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()
        synonyms = {
            "bursaries": "bursary",
            "counsellor": "counselling",
            "counselor": "counselling",
            "counseling": "counselling",
            "examinations": "exam",
            "examination": "exam",
            "fees": "fee",
            "enrol": "register",
            "enroll": "register",
            "welfare": "human adviser",
            "records": "transcript",
            "registry": "transcript",
        }
        return " ".join(synonyms.get(word, word) for word in text.split())

    def match(self, query):
        clean = self.preprocess_text(query)
        if clean in ("hi", "hello", "hey", "good morning", "good afternoon"):
            return dict(
                intent="greeting",
                title="Welcome",
                response="Hello! I can help with registration, fees, exams, transcripts and student support. What would you like to know?",
                confidence=1.0,
                source="Assistant",
                matched=True,
            )
        if clean in ("thanks", "thank you", "thank you very much"):
            return dict(
                intent="thanks",
                title="You’re welcome",
                response="You’re welcome! Ask another question whenever you need guidance.",
                confidence=1.0,
                source="Assistant",
                matched=True,
            )
        # Conservative boundaries: short fragments, ambiguity and out-of-domain queries fall back.
        word_query = self.words.transform([clean])
        if word_query.nnz == 0:
            return dict(
                intent="fallback",
                title="More detail needed",
                response=FALLBACK,
                confidence=0.0,
                source="Assistant",
                matched=False,
            )
        scores = (
            0.65 * cosine_similarity(self.words.transform([clean]), self.word_matrix)[0]
            + 0.35
            * cosine_similarity(self.chars.transform([clean]), self.char_matrix)[0]
        )
        grouped = np.zeros(len(self.entries))
        for score, owner in zip(scores, self.owners):
            grouped[owner] = max(grouped[owner], score)
        order = np.argsort(grouped)[::-1]
        best, second = grouped[order[0]], grouped[order[1]]
        if best < 0.34 or best - second < 0.055 or len(clean) < 3:
            return dict(
                intent="fallback",
                title="More detail needed",
                response=FALLBACK,
                confidence=round(float(best), 3),
                source="Assistant",
                matched=False,
            )
        e = self.entries[order[0]]
        return dict(
            intent=e["intent"],
            title=e["title"],
            response=e["response"],
            confidence=round(float(best), 3),
            source=e["source"],
            matched=True,
        )

    def get_response(self, query):
        return self.match(query)["response"]
