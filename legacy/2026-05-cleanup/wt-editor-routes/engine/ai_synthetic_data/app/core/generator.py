import pandas as pd
import numpy as np
from faker import Faker

class SyntheticGenerator:
    """Generate fake data based on inferred rules."""
    
    def __init__(self):
        self.fake = Faker('tr_TR')
        
    def generate(self, schema_dict: dict, rules: list, row_count: int = 100) -> pd.DataFrame:
        data = {}
        
        # Rule dictionary for O(1) lookup
        rule_map = {r["column_name"]: r for r in rules}
        
        for col in schema_dict.get("columns", []):
            cname = col.get("name")
            rule = rule_map.get(cname, {"rule_type": "faker", "rule_config": {"provider": "word"}})
            data[cname] = self._generate_column(rule, row_count)
            
        return pd.DataFrame(data)
        
    def _generate_column(self, rule: dict, row_count: int) -> list:
        rtype = rule.get("rule_type")
        cfg = rule.get("rule_config", {})
        
        if rtype == "faker":
            provider = cfg.get("provider", "word")
            faker_func = getattr(self.fake, provider, self.fake.word)
            return [faker_func() for _ in range(row_count)]
            
        elif rtype == "sequential":
            start = cfg.get("start", 1)
            step = cfg.get("step", 1)
            return list(range(start, start + (row_count * step), step))
            
        elif rtype == "enum":
            vals = cfg.get("values", ["A", "B"])
            weights = cfg.get("weights", None)
            # Normalize weights if they exist but don't sum to 1
            if weights:
                s = sum(weights)
                weights = [w/s for w in weights] if s > 0 else None
            return np.random.choice(vals, size=row_count, p=weights).tolist()
            
        elif rtype == "range":
            c_min = cfg.get("min", 0)
            c_max = cfg.get("max", 1000)
            mean = cfg.get("mean", (c_min + c_max) / 2)
            
            # Simple normal distribution loosely bounded
            std = (c_max - c_min) / 4 if c_max > c_min else 1
            arr = np.random.normal(loc=mean, scale=std, size=row_count)
            arr = np.clip(arr, c_min, c_max)
            return arr.tolist()
            
        elif rtype == "date_range":
            start_date = cfg.get("start_date", "-1y")
            end_date = cfg.get("end_date", "now")
            return [self.fake.date_between(start_date=start_date, end_date=end_date).isoformat() for _ in range(row_count)]
            
        # Default fallback
        return [self.fake.word() for _ in range(row_count)]
