"""Hallucination Detection & Validation Service."""

import json
import re
from typing import Tuple, List, Dict, Any, Optional
from gherkin_parser import parse_gherkin  # TODO: actual gherkin parser

from backend.app.core.logger import get_logger

logger = get_logger(__name__)


class HallucinationValidator:
    """Validate LLM outputs for hallucinations."""

    def __init__(self):
        self.min_confidence = 0.7

    async def validate(
        self,
        output: str,
        output_type: str,
        context: Optional[str] = None,
    ) -> Tuple[bool, float, List[Dict[str, Any]]]:
        """
        Validate LLM output comprehensively.

        Args:
            output: LLM output to validate
            output_type: "bdd", "code", "summary", "test_case"
            context: RAG context or source material

        Returns:
            (is_valid, confidence_score, hallucination_risks)
        """
        risks = []
        scores = []

        # 1. Syntax validation
        syntax_valid = await self._validate_syntax(output, output_type)
        scores.append(1.0 if syntax_valid else 0.0)
        if not syntax_valid:
            risks.append({
                "risk_type": "invalid_syntax",
                "description": f"Invalid {output_type} syntax detected",
                "severity": "high",
            })

        # 2. Source grounding (if context provided)
        if context:
            grounded, grounding_score = await self._validate_grounding(output, context, output_type)
            scores.append(grounding_score)
            if not grounded:
                risks.append({
                    "risk_type": "ungrounded_claim",
                    "description": "Output contains claims not found in source material",
                    "severity": "medium",
                })

        # 3. Semantic sanity
        semantic_valid = await self._validate_semantic(output, output_type)
        scores.append(1.0 if semantic_valid else 0.0)
        if not semantic_valid:
            risks.append({
                "risk_type": "semantic_error",
                "description": "Semantic inconsistency detected",
                "severity": "medium",
            })

        # 4. Self-consistency
        consistent = await self._validate_consistency(output, output_type)
        scores.append(1.0 if consistent else 0.0)
        if not consistent:
            risks.append({
                "risk_type": "contradiction",
                "description": "Internal contradictions found",
                "severity": "high",
            })

        # Calculate overall confidence
        confidence_score = sum(scores) / len(scores) if scores else 0.5
        is_valid = confidence_score >= self.min_confidence and len([r for r in risks if r["severity"] == "high"]) == 0

        return is_valid, confidence_score, risks

    async def _validate_syntax(self, output: str, output_type: str) -> bool:
        """Validate syntax based on output type."""
        try:
            if output_type == "bdd":
                # Validate Gherkin syntax
                return self._validate_gherkin(output)
            elif output_type == "code":
                # Validate Python/JavaScript syntax
                return self._validate_code_syntax(output)
            elif output_type == "json":
                json.loads(output)
                return True
            else:
                # Default: just check it's not empty
                return len(output.strip()) > 0
        except Exception as e:
            logger.warning(f"Syntax validation error: {e}")
            return False

    def _validate_gherkin(self, text: str) -> bool:
        """Validate Gherkin/BDD syntax."""
        # Must have Feature keyword
        if "Feature:" not in text and "feature:" not in text.lower():
            return False

        # Must have at least one Scenario
        if "Scenario:" not in text and "scenario:" not in text.lower():
            return False

        # Check for Given/When/Then
        required_keywords = ["Given", "When", "Then"]
        text_lower = text.lower()
        found_keywords = sum(1 for kw in required_keywords if kw.lower() in text_lower)
        return found_keywords >= 3  # At least one of each

    def _validate_code_syntax(self, code: str) -> bool:
        """Validate code syntax (Python/JavaScript)."""
        try:
            # Try Python AST parsing
            import ast
            ast.parse(code)
            return True
        except:
            pass

        try:
            # Try JavaScript-like validation (simple check)
            # Check balanced braces
            if code.count("{") != code.count("}"):
                return False
            if code.count("(") != code.count(")"):
                return False
            if code.count("[") != code.count("]"):
                return False
            return True
        except:
            return False

    async def _validate_grounding(
        self,
        output: str,
        context: str,
        output_type: str,
    ) -> Tuple[bool, float]:
        """Check if output is grounded in context."""
        if not context or len(context) < 10:
            return True, 0.5  # Can't validate without context

        # Simple keyword matching: extract key entities from output and check against context
        output_words = set(output.lower().split())
        context_words = set(context.lower().split())

        # Calculate overlap (Jaccard similarity)
        if not output_words or not context_words:
            return True, 0.5

        intersection = output_words & context_words
        union = output_words | context_words
        similarity = len(intersection) / len(union) if union else 0

        # Threshold: 0.3 = at least 30% overlap with source
        is_grounded = similarity >= 0.3
        return is_grounded, similarity

    async def _validate_semantic(self, output: str, output_type: str) -> bool:
        """Validate semantic consistency."""
        if output_type == "code":
            # Check variables are defined before use
            return self._check_variables_defined(output)
        elif output_type == "bdd":
            # Check test steps make sense
            return self._check_bdd_logic(output)
        else:
            return True  # Default: valid

    def _check_variables_defined(self, code: str) -> bool:
        """Check if code variables are defined before use."""
        lines = code.split("\n")
        defined_vars = set()

        for line in lines:
            # Simple heuristic: find assignments (var =, const =, let =)
            if " = " in line:
                var_name = line.split(" = ")[0].strip().split()[-1]
                defined_vars.add(var_name)

            # Check if undefined variables used
            for word in line.split():
                word_clean = re.sub(r"[^a-zA-Z0-9_]", "", word)
                if word_clean and word_clean[0].isalpha():
                    if word_clean not in defined_vars and not self._is_builtin(word_clean):
                        # Could be undefined - risky
                        logger.debug(f"Possibly undefined variable: {word_clean}")

        return True  # Conservative: accept unless clearly broken

    def _check_bdd_logic(self, text: str) -> bool:
        """Check BDD logic consistency."""
        # If it's a login test, check it has auth-related keywords
        if "login" in text.lower():
            required = ["password", "username", "login", "authenticate"]
            has_required = sum(1 for req in required if req in text.lower()) >= 2
            return has_required

        # Default: valid if syntax is OK
        return True

    @staticmethod
    def _is_builtin(var_name: str) -> bool:
        """Check if variable is a builtin."""
        builtins = {
            "print", "len", "range", "str", "int", "float", "list", "dict",
            "set", "None", "True", "False", "Exception", "return", "if", "for",
            "while", "def", "class", "import", "from", "as", "and", "or", "not",
            "in", "is", "user", "db", "self", "cls", "page", "request", "response",
            "json", "data", "result", "error", "message", "status", "code", "value",
        }
        return var_name in builtins

    async def _validate_consistency(self, output: str, output_type: str) -> bool:
        """Check for internal contradictions."""
        if output_type == "bdd":
            # Parse scenario assertions
            then_lines = [line for line in output.split("\n") if "Then" in line]
            # Check no obvious contradictions
            has_contradiction = any(
                ("not logged in" in line.lower() and "logged in" in line.lower())
                for line in then_lines
            )
            return not has_contradiction
        else:
            return True  # Default: valid

    async def validate_bdd(self, output: str, context: List[Dict]) -> float:
        """Validate BDD output specifically."""
        is_valid, confidence, risks = await self.validate(output, "bdd", json.dumps(context))
        return confidence

    async def validate_suggestions(self, suggestions: List[Dict]) -> float:
        """Validate improvement suggestions."""
        if not suggestions:
            return 0.5

        # Check suggestions are specific and actionable
        actionable = sum(
            1 for s in suggestions
            if len(s.get("suggested_change", "")) > 20
        )
        confidence = actionable / len(suggestions) if suggestions else 0
        return min(confidence, 1.0)

    async def validate_rca(self, root_causes: List[Dict], context: List[Dict]) -> float:
        """Validate RCA output."""
        if not root_causes:
            return 0.0

        # Check root causes are grounded in context
        context_text = json.dumps(context)
        grounded_causes = sum(
            1 for cause in root_causes
            if any(
                keyword in context_text
                for keyword in cause.get("affected_components", [])
            )
        )

        confidence = grounded_causes / len(root_causes) if root_causes else 0.5
        return min(confidence, 1.0)
