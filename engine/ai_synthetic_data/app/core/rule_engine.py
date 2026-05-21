class RuleEngine:
    """Infer data generation rules from schema analysis and semantic classification."""
    
    def infer_rules(self, schema_dict: dict) -> list:
        rules = []
        for col in schema_dict.get("columns", []):
            cname = col.get("name", "")
            cls = col.get("classification", "unknown")
            dtype = col.get("dtype", "string")
            stats = col.get("stats", {})
            
            rule_type = "faker"
            rule_config = {"provider": "word"}
            
            # Map semantic classes to Faker providers
            if cls == "tc_kimlik":
                rule_config = {"provider": "bban"} # Mocking TC via bban or custom
            elif cls == "iban":
                rule_config = {"provider": "iban"}
            elif cls == "email":
                rule_config = {"provider": "company_email"}
            elif cls == "name":
                rule_config = {"provider": "name"}
            elif cls == "phone":
                rule_config = {"provider": "phone_number"}
            elif cls == "id":
                rule_type = "sequential"
                rule_config = {"start": 1, "step": 1}
            elif cls == "enum":
                rule_type = "enum"
                tv = stats.get("top_values", {})
                if tv:
                    rule_config = {"values": list(tv.keys()), "weights": list(tv.values())}
                else:
                    rule_config = {"values": ["Value1", "Value2"]}
            elif cls == "datetime" or dtype == "datetime":
                rule_type = "date_range"
                rule_config = {"start_date": "2020-01-01", "end_date": "2025-01-01"}
            elif dtype in ["int", "float"]:
                rule_type = "range"
                rule_config = {
                    "min": stats.get("min", 0),
                    "max": stats.get("max", 1000) if stats.get("max", 0) > 0 else 1000,
                    "mean": stats.get("mean", 500)
                }
            
            rules.append({
                "column_name": cname,
                "rule_type": rule_type,
                "rule_config": rule_config
            })
            
        return rules
