"""
Environment Variable Manager
=============================

{{variable}} syntax ile degisken cozumleme.
Desteklenen syntax'lar:
  {{variable_name}}           — Ortam degiskeni
  {{env.variable_name}}       — Açık env referansi (ayni sey)
  {{$randomInt}}              — Rastgele integer
  {{$randomUUID}}             — Rastgele UUID
  {{$timestamp}}              — Unix timestamp
  {{$isoTimestamp}}           — ISO 8601 tarih
  {{$randomIBAN}}             — Rastgele TR IBAN
  {{$randomTCKN}}             — Rastgele TC Kimlik No
  {{$randomEmail}}            — Rastgele email
  {{$randomPhone}}            — Rastgele TR telefon
  {{$guid}}                   — Alias for $randomUUID
"""

import json
import random
import re
import string
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Built-in dinamik degiskenler ──────────────────────────────────────

def _random_iban() -> str:
    """Rastgele gecerli formatta TR IBAN üret (dogrulama yok)."""
    bank = random.choice(["0001", "0006", "0010", "0012", "0015", "0046", "0062", "0064", "0067"])
    digits = "".join(random.choices(string.digits, k=16))
    check = str(random.randint(10, 99))
    return f"TR{check}{bank}0{digits}"


def _random_tckn() -> str:
    """Rastgele 11 haneli TC Kimlik Numarasi (basit format, Luhn yok)."""
    first = str(random.randint(1, 9))
    rest = "".join(random.choices(string.digits, k=10))
    return first + rest


def _random_phone() -> str:
    """Rastgele TR cep telefonu."""
    prefix = random.choice(["530", "531", "532", "533", "534", "535", "536",
                             "537", "538", "539", "540", "541", "542", "543",
                             "544", "545", "546", "505", "506", "507"])
    num = "".join(random.choices(string.digits, k=7))
    return f"+90{prefix}{num}"


_BUILTINS: Dict[str, Any] = {
    "$randomInt": lambda: random.randint(1, 1_000_000),
    "$randomUUID": lambda: str(uuid.uuid4()),
    "$guid": lambda: str(uuid.uuid4()),
    "$timestamp": lambda: int(time.time()),
    "$isoTimestamp": lambda: datetime.now(timezone.utc).isoformat(),
    "$randomIBAN": _random_iban,
    "$randomTCKN": _random_tckn,
    "$randomEmail": lambda: f"test_{random.randint(1000,9999)}@nexusqa.test",
    "$randomPhone": _random_phone,
    "$randomString": lambda: "".join(random.choices(string.ascii_lowercase, k=12)),
    "$randomBoolean": lambda: random.choice(["true", "false"]),
    "$randomFloat": lambda: round(random.uniform(0.01, 99999.99), 2),
}

# Regex: {{variable_name}} veya {{env.variable_name}} veya {{$builtin}}
_VAR_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def resolve_string(
    text: str,
    variables: Dict[str, str],
) -> str:
    """
    String icindeki {{variable}} referanslarini coz.

    Args:
        text: Cozumlenecek string
        variables: Degisken adi → deger mapping'i

    Returns:
        Tüm degiskenler cozulmus string
    """
    def _replacer(match: re.Match) -> str:
        key = match.group(1).strip()

        # env. prefix'ini kaldır
        if key.startswith("env."):
            key = key[4:]

        # Built-in dinamik degisken
        if key.startswith("$") and key in _BUILTINS:
            val = _BUILTINS[key]
            return str(val() if callable(val) else val)

        # Ortam degiskeni
        if key in variables:
            return str(variables[key])

        # Cozulemedi — oldugu gibi birak
        return match.group(0)

    return _VAR_PATTERN.sub(_replacer, text)


def resolve_dict(
    data: Any,
    variables: Dict[str, str],
) -> Any:
    """
    Dict/list/string icindeki tüm {{variable}} referanslarini recursive coz.
    """
    if isinstance(data, str):
        resolved = resolve_string(data, variables)
        # Eger tüm string bir degisken ise ve deger non-string ise tipi koru
        if resolved != data and _VAR_PATTERN.fullmatch(data.strip()):
            # Tam eslesme — tip donusumu dene
            try:
                return json.loads(resolved)
            except (json.JSONDecodeError, TypeError):
                return resolved
        return resolved
    elif isinstance(data, dict):
        return {k: resolve_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_dict(item, variables) for item in data]
    else:
        return data


def merge_variables(
    *sources: Dict[str, str],
) -> Dict[str, str]:
    """
    Birden fazla degisken kaynagini birlesitir.
    Sonraki kaynaklar oncekini override eder.

    Ornek:
        merge_variables(env_vars, collection_vars, chain_vars, extracted_vars)
    """
    merged: Dict[str, str] = {}
    for source in sources:
        if source:
            merged.update(source)
    return merged


def mask_sensitive(
    variables: Dict[str, str],
    sensitive_keys: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Hassas degiskenleri maskele.
    Default hassas anahtar kelimeler: password, secret, token, key, api_key, authorization
    """
    default_sensitive = {"password", "secret", "token", "key", "api_key",
                          "authorization", "bearer", "apikey", "api_secret",
                          "client_secret", "refresh_token", "access_token"}
    sensitive = set(k.lower() for k in (sensitive_keys or []))
    sensitive.update(default_sensitive)

    masked: Dict[str, str] = {}
    for k, v in variables.items():
        if any(s in k.lower() for s in sensitive):
            # Ilk 4 ve son 4 karakteri goster, arasini maskele
            sv = str(v)
            if len(sv) > 10:
                masked[k] = sv[:4] + "*" * (len(sv) - 8) + sv[-4:]
            else:
                masked[k] = "****"
        else:
            masked[k] = str(v)
    return masked
