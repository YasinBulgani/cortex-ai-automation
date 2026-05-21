"""
NL Test Generator — Dogal Dil Aciklamalarindan Test Uretim Pipeline'i
=====================================================================

Turkce veya Ingilizce dogal dil aciklamalarini calistirilabilir test koduna/
kayitlarina donusturur.

Pipeline adimlari:
  1. Parse intent  — NL metni siniflandirir (positive, negative, security, ...)
  2. Extract entities — endpoint, method, expected status, kosullar cikarilir
  3. Match endpoints — Projedeki ApiEndpoint kayitlarina fuzzy eslestirir
  4. Resolve context — KnowledgeStore + CrossAgentMemory'den baglam toplar
  5. Generate test — Istenen formatta test uretir (api_test, bdd, pytest, playwright)

Kullanim:
    gen = NLTestGenerator(db=db, project_id="abc-123")
    result = gen.generate_from_text(
        "Transfer API'si yetersiz bakiyede 400 hatasi vermeli",
        output_format="api_test",
    )
"""

import ast
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Banking Domain Keyword Maps ─────────────────────────────────────────────

# Turkish-to-English mapping for banking terms
_TR_EN_MAP = {
    "hesap": "account",
    "bakiye": "balance",
    "transfer": "transfer",
    "havale": "transfer",
    "eft": "transfer",
    "odeme": "payment",
    "musteri": "customer",
    "kullanici": "user",
    "giris": "login",
    "oturum": "session",
    "cikis": "logout",
    "yetki": "auth",
    "kimlik": "identity",
    "kredi": "credit",
    "para cekme": "withdrawal",
    "para yatirma": "deposit",
    "kart": "card",
    "iban": "iban",
    "sifre": "password",
    "admin": "admin",
    "dogrulama": "verification",
    "onay": "confirmation",
}

# Test type indicators in Turkish and English
_TEST_TYPE_INDICATORS = {
    "positive": [
        "basarili", "gecerli", "dogru", "200", "201", "success",
        "dogrula", "donmeli", "calisir", "calismal",
    ],
    "negative": [
        "hatasi", "hata", "gecersiz", "eksik", "bos", "yanlis",
        "400", "401", "403", "404", "500",
        "error", "invalid", "missing", "empty", "wrong",
        "yetersiz", "olmayan", "bulunamayan",
    ],
    "security": [
        "guvenlik", "yetkisiz", "erisim", "injection", "xss",
        "owasp", "brute", "token", "jwt", "bola", "bfla",
        "security", "unauthorized", "forbidden", "bypass",
        "erisememeli", "erisememeli",
    ],
    "boundary": [
        "sinir", "minimum", "maksimum", "limit", "overflow",
        "boundary", "min", "max", "edge",
    ],
    "performance": [
        "performans", "hiz", "yavas", "timeout", "sure",
        "performance", "slow", "latency", "concurrent",
    ],
    "compliance": [
        "uyumluluk", "bddk", "kvkk", "pci", "masak",
        "compliance", "regulation", "audit", "log",
    ],
}

# HTTP method indicators
_METHOD_INDICATORS = {
    "GET": ["sorgulama", "goruntuleme", "listeleme", "getir", "get", "fetch", "list", "oku", "read"],
    "POST": ["olustur", "ekle", "gonder", "kaydet", "transfer", "post", "create", "submit", "yap"],
    "PUT": ["guncelle", "degistir", "update", "put", "modify"],
    "PATCH": ["kismi", "patch", "partial"],
    "DELETE": ["sil", "kaldir", "delete", "remove", "iptal"],
}

# Status code indicators
_STATUS_PATTERNS = [
    (re.compile(r"\b(200)\b"), 200),
    (re.compile(r"\b(201)\b"), 201),
    (re.compile(r"\b(204)\b"), 204),
    (re.compile(r"\b(400)\b"), 400),
    (re.compile(r"\b(401)\b"), 401),
    (re.compile(r"\b(403)\b"), 403),
    (re.compile(r"\b(404)\b"), 404),
    (re.compile(r"\b(409)\b"), 409),
    (re.compile(r"\b(422)\b"), 422),
    (re.compile(r"\b(429)\b"), 429),
    (re.compile(r"\b(500)\b"), 500),
    (re.compile(r"\b(502)\b"), 502),
    (re.compile(r"\b(503)\b"), 503),
]

# Path extraction pattern
_PATH_PATTERN = re.compile(r"(/[a-zA-Z0-9_\-{}/]+)")


class NLTestGenerator:
    """
    Dogal dil aciklamalarindan test uretim servisi.

    Her proje baglami icinde calisir ve projenin mevcut
    endpoint envanterini kullanarak eslestirme yapar.
    """

    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PUBLIC API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def generate_from_text(
        self,
        text: str,
        output_format: str = "api_test",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ana pipeline: Dogal dil aciklamasindan test uretir.

        Args:
            text:          Dogal dil test aciklamasi (TR veya EN)
            output_format: Cikti formati — "api_test", "bdd", "pytest", "playwright"
            context:       Ek baglam bilgisi (opsiyonel)

        Returns:
            Pipeline sonuc dict'i — parsed_intent, matched_endpoints,
            generated output, validation bilgileri.
        """
        t0 = time.time()
        model_used = "unknown"

        # Step 1: Parse intent
        parsed_intent = self._parse_intent(text)

        # Step 2: Match endpoints
        matched_endpoints = self._match_endpoints(parsed_intent)

        # Step 3: Resolve context
        resolved_context = self._resolve_context(text, parsed_intent, context)

        # Step 4: Generate via LLM
        generated = {"test_cases": [], "code": None, "gherkin": None}  # type: Dict[str, Any]
        validation = {"syntax_valid": True, "warnings": []}  # type: Dict[str, Any]

        try:
            gen_result = self._llm_generate(
                text=text,
                parsed_intent=parsed_intent,
                matched_endpoints=matched_endpoints,
                resolved_context=resolved_context,
                output_format=output_format,
            )
            generated = gen_result.get("generated", generated)
            model_used = gen_result.get("model_used", "unknown")

            # Step 5: Validate output
            if output_format == "pytest" and generated.get("code"):
                validation = self.validate_code(generated["code"], "python")
            elif output_format == "playwright" and generated.get("code"):
                validation = self.validate_code(generated["code"], "typescript")

            # Step 5b: For api_test format, persist to DB
            if output_format == "api_test" and generated.get("test_cases"):
                generated["test_cases"] = self._persist_test_cases(
                    generated["test_cases"],
                    matched_endpoints,
                    model_used,
                )

        except Exception as exc:
            logger.warning("NLTestGenerator LLM generation hatasi: %s", exc)
            validation["warnings"].append("LLM uretim hatasi: %s" % str(exc)[:200])
            validation["syntax_valid"] = False

        duration_ms = round((time.time() - t0) * 1000, 1)

        return {
            "input_text": text,
            "parsed_intent": parsed_intent,
            "matched_endpoints": matched_endpoints,
            "output_format": output_format,
            "generated": generated,
            "validation": validation,
            "model_used": model_used,
            "duration_ms": duration_ms,
        }

    def batch_generate(
        self,
        texts: List[str],
        output_format: str = "api_test",
    ) -> Dict[str, Any]:
        """
        Birden fazla NL aciklamasindan toplu test uretimi.

        Returns:
            {
                "results": [...],
                "summary": { total, succeeded, failed, total_duration_ms },
            }
        """
        t0 = time.time()
        results = []  # type: List[Dict[str, Any]]
        succeeded = 0
        failed = 0

        for text in texts:
            try:
                result = self.generate_from_text(text, output_format=output_format)
                results.append(result)
                if result.get("validation", {}).get("syntax_valid", False):
                    succeeded += 1
                else:
                    failed += 1
            except Exception as exc:
                logger.warning("Batch generate tekil hata: %s", exc)
                results.append({
                    "input_text": text,
                    "error": str(exc)[:300],
                    "parsed_intent": {},
                    "matched_endpoints": [],
                    "output_format": output_format,
                    "generated": {"test_cases": [], "code": None, "gherkin": None},
                    "validation": {"syntax_valid": False, "warnings": [str(exc)[:200]]},
                    "model_used": "unknown",
                    "duration_ms": 0.0,
                })
                failed += 1

        total_duration_ms = round((time.time() - t0) * 1000, 1)

        return {
            "results": results,
            "summary": {
                "total": len(texts),
                "succeeded": succeeded,
                "failed": failed,
                "total_duration_ms": total_duration_ms,
            },
        }

    def suggest_from_endpoint(
        self,
        endpoint_id: str,
        count: int = 5,
    ) -> Dict[str, Any]:
        """
        Verilen endpoint icin QA muhendisinin yazabilecegi
        dogal dil test aciklamalari oner.

        Args:
            endpoint_id: ApiEndpoint kayit ID'si
            count:       Kac oneri uretilsin (default 5)

        Returns:
            { endpoint_id, endpoint, suggestions: [{text, test_type, priority}] }
        """
        from app.domains.api_testing.models import ApiEndpoint

        ep = self.db.get(ApiEndpoint, endpoint_id)
        if ep is None:
            return {
                "endpoint_id": endpoint_id,
                "endpoint": "unknown",
                "suggestions": [],
            }

        endpoint_str = "%s %s" % (ep.method, ep.path)

        # Build suggestions via LLM
        suggestions = []  # type: List[Dict[str, str]]
        try:
            suggestions = self._llm_suggest(ep, count)
        except Exception as exc:
            logger.warning("NLTestGenerator suggest hatasi: %s", exc)
            # Fallback: rule-based suggestions
            suggestions = self._rule_based_suggestions(ep, count)

        return {
            "endpoint_id": endpoint_id,
            "endpoint": endpoint_str,
            "suggestions": suggestions[:count],
        }

    def validate_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Uretilen kodun temel syntax dogrulamasini yapar.

        Args:
            code:     Dogrulanacak kod string'i
            language: "python" veya "typescript"

        Returns:
            {"valid": bool, "errors": List[str]}
        """
        errors = []  # type: List[str]

        if language == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append("Python syntax hatasi satir %s: %s" % (e.lineno, e.msg))
        elif language == "typescript":
            # Basic structural checks for TypeScript / Playwright
            if "import" not in code and "require" not in code:
                errors.append("Import/require ifadesi bulunamadi")
            if not re.search(r"\b(describe|test|it)\s*\(", code):
                errors.append("describe/test/it blogu bulunamadi")
            # Check balanced braces
            open_count = code.count("{")
            close_count = code.count("}")
            if open_count != close_count:
                errors.append(
                    "Dengesiz suslu parantez: %d acik, %d kapali" % (open_count, close_count)
                )
        else:
            errors.append("Desteklenmeyen dil: %s" % language)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNAL: PARSE INTENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _parse_intent(self, text: str) -> Dict[str, Any]:
        """
        Dogal dil metninden test intent'ini cikar.

        Returns:
            {
                test_type, method, path_hint, expected_status,
                conditions, entities,
            }
        """
        text_lower = self._normalize_turkish(text.lower())

        # -- Detect test type --
        test_type = self._detect_test_type(text_lower)

        # -- Detect HTTP method --
        method = self._detect_method(text_lower)

        # -- Extract path hint --
        path_hint = self._extract_path_hint(text)

        # -- Extract expected status --
        expected_status = self._extract_status(text_lower)

        # -- Extract conditions --
        conditions = self._extract_conditions(text_lower)

        # -- Extract entities (banking domain terms) --
        entities = self._extract_entities(text_lower)

        return {
            "test_type": test_type,
            "method": method,
            "path_hint": path_hint,
            "expected_status": expected_status,
            "conditions": conditions,
            "entities": entities,
        }

    def _normalize_turkish(self, text: str) -> str:
        """Turkce karakterleri ASCII'ye normalize et (arama icin)."""
        replacements = {
            "\u00e7": "c", "\u011f": "g", "\u0131": "i", "\u00f6": "o",
            "\u015f": "s", "\u00fc": "u",
            "\u00c7": "C", "\u011e": "G", "\u0130": "I", "\u00d6": "O",
            "\u015e": "S", "\u00dc": "U",
        }
        for tr_char, en_char in replacements.items():
            text = text.replace(tr_char, en_char)
        return text

    def _detect_test_type(self, text: str) -> str:
        """Metindeki ipuclarina gore test tipini belirle."""
        scores = {}  # type: Dict[str, int]
        for ttype, keywords in _TEST_TYPE_INDICATORS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[ttype] = score

        if not scores:
            return "positive"  # default

        return max(scores, key=lambda k: scores[k])

    def _detect_method(self, text: str) -> Optional[str]:
        """Metindeki ipuclarina gore HTTP method belirle."""
        # Direct mention: "GET", "POST", etc.
        direct = re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\b", text, re.IGNORECASE)
        if direct:
            return direct.group(1).upper()

        # Keyword-based
        scores = {}  # type: Dict[str, int]
        for method, keywords in _METHOD_INDICATORS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[method] = score

        if scores:
            return max(scores, key=lambda k: scores[k])
        return None

    def _extract_path_hint(self, text: str) -> Optional[str]:
        """Metinden URL path ipucu cikar."""
        match = _PATH_PATTERN.search(text)
        if match:
            path = match.group(1)
            # Filter out very short paths that are likely false positives
            if len(path) > 3:
                return path
        return None

    def _extract_status(self, text: str) -> Optional[int]:
        """Metinden beklenen HTTP status code cikar."""
        for pattern, code in _STATUS_PATTERNS:
            if pattern.search(text):
                return code
        # Keyword-based status inference
        if "basarili" in text or "donmeli" in text:
            # Check for error keywords
            if any(kw in text for kw in ["hata", "yetersiz", "gecersiz", "yetkisiz"]):
                if "400" not in text and "hata" in text:
                    return 400
                if "yetkisiz" in text or "erisememeli" in text:
                    return 403
        return None

    def _extract_conditions(self, text: str) -> List[str]:
        """Metindeki test kosullarini cikar."""
        conditions = []  # type: List[str]

        # Common condition patterns
        condition_patterns = [
            (r"(?:sonra|ardından|ardinda)\s+(.+?)(?:\.|$)", "precondition"),
            (r"(?:iken|olduğunda|oldugunda|durumunda)\s+(.+?)(?:\s|$)", "state"),
            (r"(?:yetersiz|gecersiz|eksik|bos)\s+(\w+)", "invalid_field"),
        ]
        for pattern, ctype in condition_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                conditions.append("%s: %s" % (ctype, m.strip()[:100]))

        return conditions

    def _extract_entities(self, text: str) -> Dict[str, str]:
        """Banking domain entity'lerini cikar."""
        entities = {}  # type: Dict[str, str]
        for tr_term, en_term in _TR_EN_MAP.items():
            if tr_term in text:
                entities[en_term] = tr_term

        # Also check English terms
        for en_term in _TR_EN_MAP.values():
            if en_term in text and en_term not in entities:
                entities[en_term] = en_term

        return entities

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNAL: ENDPOINT MATCHING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _match_endpoints(
        self, parsed_intent: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Projenin ApiEndpoint envanterinden intent'e uygun endpoint'leri bul.

        Fuzzy matching: path segment'leri, method, entity isimleri.
        """
        from app.domains.api_testing.models import ApiEndpoint, ApiSpec
        from sqlalchemy import select

        # Get all endpoints for this project's specs
        stmt = (
            select(ApiEndpoint)
            .join(ApiSpec, ApiEndpoint.spec_id == ApiSpec.id)
            .where(ApiSpec.project_id == self.project_id)
        )
        endpoints = list(self.db.scalars(stmt))

        if not endpoints:
            return []

        method_hint = parsed_intent.get("method")
        path_hint = parsed_intent.get("path_hint")
        entities = parsed_intent.get("entities", {})

        scored = []  # type: List[Tuple[float, ApiEndpoint]]

        for ep in endpoints:
            score = 0.0

            # Method match
            if method_hint and ep.method.upper() == method_hint.upper():
                score += 0.3

            # Path match
            if path_hint:
                score += self._fuzzy_path_score(path_hint, ep.path)

            # Entity/keyword match in path
            ep_path_lower = ep.path.lower()
            for en_term in entities:
                if en_term in ep_path_lower:
                    score += 0.2
                # Also check Turkish term
                tr_term = entities[en_term]
                if tr_term in ep_path_lower:
                    score += 0.2

            # Summary / description match
            ep_summary_lower = (ep.summary or "").lower()
            ep_desc_lower = (ep.description or "").lower()
            for en_term in entities:
                if en_term in ep_summary_lower or en_term in ep_desc_lower:
                    score += 0.1

            # Tags match
            ep_tags_str = " ".join(ep.tags or []).lower()
            for en_term in entities:
                if en_term in ep_tags_str:
                    score += 0.1

            if score > 0.0:
                scored.append((score, ep))

        # Sort by score descending, take top 5
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "endpoint_id": ep.id,
                "method": ep.method,
                "path": ep.path,
                "confidence": round(min(sc, 1.0), 2),
            }
            for sc, ep in scored[:5]
        ]

    def _fuzzy_path_score(self, hint: str, actual: str) -> float:
        """Path segment'leri arasinda fuzzy benzerlik skoru hesapla."""
        hint_segments = set(
            s.lower().strip("{}")
            for s in hint.strip("/").split("/")
            if s
        )
        actual_segments = set(
            s.lower().strip("{}")
            for s in actual.strip("/").split("/")
            if s
        )

        if not hint_segments or not actual_segments:
            return 0.0

        intersection = hint_segments & actual_segments
        if not intersection:
            # Partial substring match
            partial = 0
            for hs in hint_segments:
                for acts in actual_segments:
                    if hs in acts or acts in hs:
                        partial += 1
            return min(partial * 0.1, 0.3)

        return min(len(intersection) / max(len(hint_segments), 1) * 0.4, 0.4)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNAL: CONTEXT RESOLUTION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _resolve_context(
        self,
        text: str,
        parsed_intent: Dict[str, Any],
        extra_context: Optional[Dict[str, Any]],
    ) -> str:
        """
        KnowledgeStore + CrossAgentMemory'den baglam topla.
        """
        parts = []  # type: List[str]

        # KnowledgeStore context
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self.project_id)
            try:
                chunks = store.retrieve(text, top_k=3, sources=["agent_insight", "execution", "error_pattern"])
                if chunks:
                    parts.append("## BILGI DEPOSUNDAN ILGILI BULGULAR")
                    for c in chunks:
                        parts.append("- [%s] %s" % (c.source, c.content[:200]))
            finally:
                store.close()
        except Exception as exc:
            logger.debug("KnowledgeStore context hatasi: %s", exc)

        # CrossAgentMemory context
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            entities = parsed_intent.get("entities", {})
            tags = list(entities.keys())[:5]
            agent_context = CrossAgentMemory.get_context_for_agent(
                "nl_test_generator",
                project_id=self.project_id,
                relevant_tags=tags if tags else None,
            )
            if agent_context:
                parts.append(agent_context)
        except Exception as exc:
            logger.debug("CrossAgentMemory context hatasi: %s", exc)

        # Extra user-provided context
        if extra_context:
            parts.append("## EK BAGLAM")
            for k, v in extra_context.items():
                parts.append("- %s: %s" % (k, str(v)[:200]))

        return "\n\n".join(parts) if parts else ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNAL: LLM GENERATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _llm_generate(
        self,
        text: str,
        parsed_intent: Dict[str, Any],
        matched_endpoints: List[Dict[str, Any]],
        resolved_context: str,
        output_format: str,
    ) -> Dict[str, Any]:
        """
        LLM'i kullanarak test uretir.

        Returns:
            {"generated": {...}, "model_used": str}
        """
        from app.domains.ai.smart_model_router import route_model
        from app.domains.ai.service import call_llm

        # Route model
        rec = route_model(
            task_type="test_generation",
            complexity="medium",
            has_financial=any(
                t in text.lower()
                for t in ["transfer", "havale", "odeme", "bakiye", "kredi", "iban"]
            ),
        )
        model_name = rec.model

        # Build system prompt
        system_prompt = self._build_system_prompt(output_format)

        # Build user prompt
        user_prompt = self._build_user_prompt(
            text, parsed_intent, matched_endpoints, resolved_context, output_format,
        )

        # Few-shot examples
        try:
            from app.domains.ai.few_shot_bank import get_few_shot_examples
            entities = parsed_intent.get("entities", {})
            keywords = list(entities.keys())[:3]
            examples = get_few_shot_examples(
                "test_generation", endpoint_keywords=keywords, max_examples=1,
            )
            if examples:
                system_prompt += "\n\n" + examples
        except Exception:
            pass

        # Call LLM
        raw_response = call_llm(
            system=system_prompt,
            user_content=user_prompt,
            json_mode=(output_format == "api_test"),
            model=model_name,
            temperature=rec.temperature,
            max_tokens=rec.max_tokens,
            _trace_agent="nl_test_generator",
            _trace_phase=output_format,
            _trace_project_id=self.project_id,
        )

        # Parse response
        generated = self._parse_llm_response(raw_response, output_format)

        return {
            "generated": generated,
            "model_used": model_name,
        }

    def _build_system_prompt(self, output_format: str) -> str:
        """Output formatina gore system prompt olustur."""
        base = (
            "Sen bankacilik sektorunde uzman bir QA test muhendisisin.\n"
            "Turkce ve Ingilizce dogal dil aciklamalarini analiz ederek "
            "yuksek kaliteli test senaryolari uretiyorsun.\n"
            "Bankacilik domain terimleri: hesap, bakiye, transfer, havale, EFT, "
            "odeme, musteri, IBAN, kredi, para cekme, para yatirma, kart.\n"
        )

        if output_format == "api_test":
            return base + (
                "\nJSON formatinda test case'ler uret. Her test case su alanlari icermeli:\n"
                "- title: Test basligi\n"
                "- description: Aciklama\n"
                "- test_type: positive | negative | security | boundary | compliance | performance\n"
                "- priority: P0 | P1 | P2 | P3\n"
                "- request_method: HTTP method\n"
                "- request_path: API path\n"
                "- request_headers: {} header'lar\n"
                "- request_body: {} istek govdesi (opsiyonel)\n"
                "- assertions: [{type, path, operator, expected}] assertion listesi\n"
                "- ai_reasoning: Neden bu testi olusturdugunun aciklamasi\n"
                "\nYanitini su JSON formatinda ver:\n"
                '{"test_cases": [...]}\n'
            )
        elif output_format == "bdd":
            return base + (
                "\nGherkin (BDD) formatinda Turkce senaryo uret.\n"
                "Ozellik/Senaryo/Verilen/Ve/Zaman/O zaman kaliplarini kullan.\n"
                "Yanitini su JSON formatinda ver:\n"
                '{"gherkin": "Ozellik: ...\\nSenaryo: ...\\n..."}\n'
            )
        elif output_format == "pytest":
            return base + (
                "\nPython pytest kodu uret. requests kutuphanesini kullan.\n"
                "Her test fonksiyonu icin assert ifadeleri ekle.\n"
                "Fixture'lar, parametrize decorator ve docstring ekle.\n"
                "Yanitini su JSON formatinda ver:\n"
                '{"code": "import pytest\\nimport requests\\n..."}\n'
            )
        elif output_format == "playwright":
            return base + (
                "\nPlaywright TypeScript test kodu uret.\n"
                "test.describe ve test blokları kullan.\n"
                "API testing icin request fixture'ini kullan.\n"
                "Yanitini su JSON formatinda ver:\n"
                '{"code": "import { test, expect } from \'@playwright/test\';\\n..."}\n'
            )

        return base

    def _build_user_prompt(
        self,
        text: str,
        parsed_intent: Dict[str, Any],
        matched_endpoints: List[Dict[str, Any]],
        resolved_context: str,
        output_format: str,
    ) -> str:
        """User prompt'unu olustur."""
        parts = [
            "## KULLANICI ISTEGI",
            text,
            "",
            "## ANALIZ EDILEN INTENT",
            "Test tipi: %s" % parsed_intent.get("test_type", "unknown"),
        ]

        method = parsed_intent.get("method")
        if method:
            parts.append("HTTP method: %s" % method)

        path_hint = parsed_intent.get("path_hint")
        if path_hint:
            parts.append("Path ipucu: %s" % path_hint)

        expected_status = parsed_intent.get("expected_status")
        if expected_status:
            parts.append("Beklenen status: %d" % expected_status)

        conditions = parsed_intent.get("conditions", [])
        if conditions:
            parts.append("Kosullar: %s" % ", ".join(conditions))

        entities = parsed_intent.get("entities", {})
        if entities:
            parts.append("Tespitler: %s" % json.dumps(entities, ensure_ascii=False))

        if matched_endpoints:
            parts.append("")
            parts.append("## ESLESEN ENDPOINT'LER")
            for ep in matched_endpoints[:3]:
                parts.append("- %s %s (confidence: %.2f)" % (ep["method"], ep["path"], ep["confidence"]))

        if resolved_context:
            parts.append("")
            parts.append(resolved_context)

        parts.append("")
        parts.append("Cikti formati: %s" % output_format)

        return "\n".join(parts)

    def _parse_llm_response(
        self, raw: str, output_format: str,
    ) -> Dict[str, Any]:
        """LLM yanitini parse et."""
        result = {"test_cases": [], "code": None, "gherkin": None}  # type: Dict[str, Any]

        # Try JSON parse
        parsed = None  # type: Any
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # Try to extract JSON from markdown code block
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                except (json.JSONDecodeError, TypeError):
                    pass

        if parsed is None:
            # For code formats, return raw text as code
            if output_format in ("pytest", "playwright"):
                code_match = re.search(r"```(?:python|typescript|ts)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
                if code_match:
                    result["code"] = code_match.group(1).strip()
                else:
                    result["code"] = raw.strip()
            elif output_format == "bdd":
                result["gherkin"] = raw.strip()
            return result

        # Process parsed JSON
        if isinstance(parsed, dict):
            if "test_cases" in parsed:
                result["test_cases"] = parsed["test_cases"]
            if "code" in parsed:
                result["code"] = parsed["code"]
            if "gherkin" in parsed:
                result["gherkin"] = parsed["gherkin"]
        elif isinstance(parsed, list):
            result["test_cases"] = parsed

        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNAL: PERSIST TEST CASES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _persist_test_cases(
        self,
        test_cases: List[Dict[str, Any]],
        matched_endpoints: List[Dict[str, Any]],
        model_used: str,
    ) -> List[Dict[str, Any]]:
        """
        LLM tarafindan uretilen test case'leri DB'ye kaydet.

        Returns:
            Kaydedilen test case'lerin dict listesi (id dahil).
        """
        from app.domains.api_testing.models import ApiTestCase

        # Best-match endpoint id
        endpoint_id = None  # type: Optional[str]
        if matched_endpoints:
            endpoint_id = matched_endpoints[0].get("endpoint_id")

        persisted = []  # type: List[Dict[str, Any]]

        for tc_data in test_cases:
            try:
                tc = ApiTestCase(
                    project_id=self.project_id,
                    endpoint_id=endpoint_id,
                    title=str(tc_data.get("title", "NL-Generated Test"))[:500],
                    description=tc_data.get("description"),
                    test_type=tc_data.get("test_type", "positive"),
                    priority=tc_data.get("priority", "P2"),
                    request_method=str(tc_data.get("request_method", "GET"))[:16],
                    request_path=str(tc_data.get("request_path", "/"))[:1000],
                    request_headers=tc_data.get("request_headers", {}),
                    request_params=tc_data.get("request_params", {}),
                    request_body=tc_data.get("request_body"),
                    assertions=tc_data.get("assertions", []),
                    ai_generated=True,
                    ai_model=model_used,
                    ai_confidence=tc_data.get("ai_confidence", 0.7),
                    ai_reasoning=tc_data.get("ai_reasoning"),
                    owasp_category=tc_data.get("owasp_category"),
                    regulation=tc_data.get("regulation"),
                )
                self.db.add(tc)
                self.db.flush()

                persisted.append({
                    "id": tc.id,
                    "title": tc.title,
                    "test_type": tc.test_type,
                    "priority": tc.priority,
                    "request_method": tc.request_method,
                    "request_path": tc.request_path,
                })
            except Exception as exc:
                logger.warning("Test case kaydi hatasi: %s", exc)
                continue

        if persisted:
            try:
                self.db.commit()
            except Exception as exc:
                logger.warning("Test case commit hatasi: %s", exc)
                self.db.rollback()
                return []

        # Publish to CrossAgentMemory
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            CrossAgentMemory.publish(
                agent_name="nl_test_generator",
                event_type="test_generated",
                data={
                    "count": len(persisted),
                    "test_types": list(set(p["test_type"] for p in persisted)),
                    "project_id": self.project_id,
                },
                tags=["nl_generation", "api_test"],
            )
        except Exception:
            pass

        return persisted

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNAL: SUGGEST VIA LLM
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _llm_suggest(self, endpoint: Any, count: int) -> List[Dict[str, str]]:
        """LLM kullanarak endpoint icin test onerileri uret."""
        from app.domains.ai.service import call_llm

        system = (
            "Sen bankacilik test uzmanisisin. Verilen API endpoint icin "
            "bir QA muhendisinin dogal dilde yazabilecegi test aciklamalari oner.\n"
            "Her oneri icin JSON formatinda su alanlari doldur:\n"
            "- text: Turkce dogal dil test aciklamasi\n"
            "- test_type: positive | negative | security | boundary | compliance\n"
            "- priority: P0 | P1 | P2 | P3\n"
            '\nYanitini su JSON formatinda ver: {"suggestions": [...]}\n'
        )

        ep_info = (
            "Endpoint: %s %s\n"
            "Ozet: %s\n"
            "Auth gerekli: %s\n"
            "Finansal: %s\n"
            "PII: %s\n"
            "Risk seviyesi: %s\n"
            "%d adet oneri uret."
        ) % (
            endpoint.method,
            endpoint.path,
            endpoint.summary or "Yok",
            "Evet" if endpoint.auth_required else "Hayir",
            "Evet" if endpoint.has_financial else "Hayir",
            "Evet" if endpoint.has_pii else "Hayir",
            endpoint.risk_level or "medium",
            count,
        )

        raw = call_llm(
            system=system,
            user_content=ep_info,
            json_mode=True,
            _trace_agent="nl_test_generator",
            _trace_phase="suggest",
            _trace_project_id=self.project_id,
        )

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "suggestions" in parsed:
                return parsed["suggestions"][:count]
            if isinstance(parsed, list):
                return parsed[:count]
        except (json.JSONDecodeError, TypeError):
            pass

        return []

    def _rule_based_suggestions(self, endpoint: Any, count: int) -> List[Dict[str, str]]:
        """Kural tabanli fallback: LLM basarisiz olursa basit oneriler uret."""
        suggestions = []  # type: List[Dict[str, str]]
        method = endpoint.method.upper()
        path = endpoint.path

        # Positive test
        suggestions.append({
            "text": "%s %s endpoint'ine gecerli parametrelerle istek gonderildiginde basarili yanit donmeli" % (method, path),
            "test_type": "positive",
            "priority": "P1",
        })

        # Negative - auth
        if endpoint.auth_required:
            suggestions.append({
                "text": "%s %s endpoint'ine token olmadan istek gonderildiginde 401 donmeli" % (method, path),
                "test_type": "negative",
                "priority": "P0",
            })

        # Security - BOLA
        suggestions.append({
            "text": "Baska kullanicinin kaynagina %s %s ile erisim denendiginde 403 donmeli" % (method, path),
            "test_type": "security",
            "priority": "P0",
        })

        # Boundary
        if method in ("POST", "PUT", "PATCH"):
            suggestions.append({
                "text": "%s %s endpoint'ine bos body gonderildiginde uygun hata mesaji donmeli" % (method, path),
                "test_type": "boundary",
                "priority": "P2",
            })

        # Financial-specific
        if endpoint.has_financial:
            suggestions.append({
                "text": "%s %s ile yetersiz bakiyede islem yapildiginda 400 hatasi donmeli" % (method, path),
                "test_type": "negative",
                "priority": "P0",
            })

        # Compliance
        if endpoint.has_pii:
            suggestions.append({
                "text": "%s %s endpoint'i KVKK uyumlu olarak hassas verileri maskelemeli" % (method, path),
                "test_type": "compliance",
                "priority": "P1",
            })

        return suggestions[:count]
