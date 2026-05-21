import re

class SemanticClassifier:
    """Classify columns to detect meaning and PII."""
    
    def __init__(self):
        self.rules = [
            {"pattern": r".*(tc|kimlik|tckn).*", "class": "tc_kimlik", "pii": True},
            {"pattern": r".*iban.*", "class": "iban", "pii": True},
            {"pattern": r".*(mail).*", "class": "email", "pii": True},
            {"pattern": r".*(name|isim|ad).*", "class": "name", "pii": True},
            {"pattern": r".*(phone|telefon|tel).*", "class": "phone", "pii": True},
            {"pattern": r".*(balance|bakiye).*", "class": "currency", "pii": False},
            {"pattern": r".*(amount|tutar).*", "class": "currency", "pii": False},
            {"pattern": r".*(segment|type|durum).*", "class": "enum", "pii": False},
            {"pattern": r".*(id).*", "class": "id", "pii": False},
            {"pattern": r".*(date|tarih).*", "class": "datetime", "pii": False},
        ]
        
    def classify_column(self, col_name: str) -> dict:
        lc_name = col_name.lower()
        for rule in self.rules:
            if re.match(rule["pattern"], lc_name):
                return {"classification": rule["class"], "pii": rule["pii"]}
        return {"classification": "unknown", "pii": False}
        
    def enrich_schema(self, schema_dict: dict) -> dict:
        """Enrich schema dictionary with semantic classifications."""
        for col in schema_dict.get("columns", []):
            cls_info = self.classify_column(col["name"])
            col["classification"] = cls_info["classification"]
            col["pii"] = cls_info["pii"]
        return schema_dict
