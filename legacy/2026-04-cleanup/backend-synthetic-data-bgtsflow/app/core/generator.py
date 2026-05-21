"""
Synthetic Data Generator — produces realistic data from analyzed schemas and rules.
Uses Faker with locale support, distribution-aware numeric generation,
and referential integrity preservation.
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from faker import Faker


class SyntheticGenerator:
    """Generates synthetic datasets given schema + rules."""

    def __init__(self, locale: str = "tr_TR"):
        self.fake = Faker(locale)
        self.fake_en = Faker("en_US")
        Faker.seed(0)
        random.seed(42)
        np.random.seed(42)

    def generate(
        self,
        schema: dict,
        rules: list[dict],
        row_count: int = 1000,
        scenario_overrides: Optional[dict] = None,
    ) -> pd.DataFrame:
        """
        Generate a synthetic DataFrame.
        
        Args:
            schema: Detected schema dict with columns metadata.
            rules: List of inferred generation rules.
            row_count: Number of rows to generate.
            scenario_overrides: Optional dict of column → override config.
        """
        # Build a rule lookup: column_name → list of rules
        rule_map = {}
        for rule in rules:
            col = rule["column_name"]
            if col not in rule_map:
                rule_map[col] = []
            rule_map[col].append(rule)

        # Apply scenario overrides
        if scenario_overrides:
            for col, override in scenario_overrides.items():
                rule_map[col] = [override]

        # Generate each column
        data = {}
        columns = schema.get("columns", [])

        for col_info in columns:
            col_name = col_info["name"]
            col_rules = rule_map.get(col_name, [])
            data[col_name] = self._generate_column(col_info, col_rules, row_count, data)

        df = pd.DataFrame(data)
        return df

    def _generate_column(
        self, col_info: dict, rules: list, row_count: int, existing_data: dict
    ) -> list:
        """Generate values for a single column based on its rules."""
        values = []

        # Find the primary rule (non-nullable, non-temporal)
        primary_rule = None
        null_rule = None
        temporal_rule = None

        for r in rules:
            if r["rule_type"] == "nullable":
                null_rule = r
            elif r["rule_type"] == "temporal_order":
                temporal_rule = r
            else:
                primary_rule = r

        # Generate base values
        if primary_rule:
            rtype = primary_rule["rule_type"]
            config = primary_rule.get("rule_config", {})

            if rtype == "faker":
                values = self._gen_faker(config, row_count)
            elif rtype == "range":
                values = self._gen_range(config, row_count)
            elif rtype == "enum":
                values = self._gen_enum(config, row_count)
            elif rtype == "sequential":
                values = self._gen_sequential(config, row_count)
            elif rtype == "date_range":
                values = self._gen_date_range(config, row_count)
            elif rtype == "random_string":
                values = self._gen_random_string(config, row_count)
            else:
                values = [None] * row_count
        else:
            # No rule — generate based on dtype
            dtype = col_info.get("dtype", "object")
            if "int" in dtype:
                values = list(range(1, row_count + 1))
            elif "float" in dtype:
                values = [round(random.uniform(0, 1000), 2) for _ in range(row_count)]
            else:
                values = [self.fake.word() for _ in range(row_count)]

        # Apply temporal ordering
        if temporal_rule and temporal_rule["rule_config"].get("after_column"):
            ref_col = temporal_rule["rule_config"]["after_column"]
            if ref_col in existing_data:
                min_off = temporal_rule["rule_config"].get("min_offset_days", 1)
                max_off = temporal_rule["rule_config"].get("max_offset_days", 365)
                values = []
                for ref_val in existing_data[ref_col]:
                    if isinstance(ref_val, (datetime,)):
                        offset = timedelta(days=random.randint(min_off, max_off))
                        values.append(ref_val + offset)
                    else:
                        values.append(None)

        # Apply null injection
        if null_rule:
            ratio = null_rule["rule_config"].get("null_ratio", 0)
            null_count = int(row_count * ratio)
            indices = random.sample(range(row_count), min(null_count, row_count))
            for idx in indices:
                values[idx] = None

        return values

    # ── Specific generators ─────────────────────────────────────────────────────

    def _gen_faker(self, config: dict, count: int) -> list:
        """Generate using a Faker provider."""
        provider = config.get("provider", "word")
        locale = config.get("locale")
        args = config.get("args", {})

        fake = self.fake if locale == "tr_TR" else self.fake_en if locale else self.fake

        if provider == "sequential":
            return list(range(1, count + 1))

        if provider == "random_element":
            elements = args.get("elements", ["A", "B"])
            return [random.choice(elements) for _ in range(count)]

        if provider == "numerify":
            text = args.get("text", "###")
            return [fake.numerify(text) for _ in range(count)]

        # Generic Faker method call
        try:
            method = getattr(fake, provider)
            return [method(**args) for _ in range(count)]
        except Exception:
            return [fake.word() for _ in range(count)]

    def _gen_range(self, config: dict, count: int) -> list:
        """Generate numeric values within a range, optionally distribution-aware."""
        dist = config.get("distribution", "uniform")
        min_val = config.get("min", 0)
        max_val = config.get("max", 100)

        if dist == "normal":
            mean = config.get("mean", (min_val + max_val) / 2)
            std = config.get("std", (max_val - min_val) / 6)
            values = np.random.normal(mean, std, count)
            values = np.clip(values, min_val, max_val)
        else:
            values = np.random.uniform(min_val, max_val, count)

        # If original was integer, round
        if isinstance(min_val, int) and isinstance(max_val, int):
            return [int(round(v)) for v in values]
        return [round(float(v), 2) for v in values]

    def _gen_enum(self, config: dict, count: int) -> list:
        """Generate categorical values with weighted probabilities."""
        values_list = config.get("values", ["A", "B"])
        weights = config.get("weights")

        if weights and len(weights) == len(values_list):
            # Normalize weights to sum to 1
            total = sum(weights)
            probs = [w / total for w in weights]
            return list(np.random.choice(values_list, size=count, p=probs))
        else:
            return [random.choice(values_list) for _ in range(count)]

    def _gen_sequential(self, config: dict, count: int) -> list:
        """Generate sequential IDs."""
        start = config.get("start", 1)
        step = config.get("step", 1)
        return list(range(start, start + count * step, step))

    def _gen_date_range(self, config: dict, count: int) -> list:
        """Generate random dates within a range."""
        try:
            start = datetime.strptime(str(config.get("start_date", "2020-01-01"))[:10], "%Y-%m-%d")
            end = datetime.strptime(str(config.get("end_date", "2025-12-31"))[:10], "%Y-%m-%d")
        except Exception:
            start = datetime(2020, 1, 1)
            end = datetime(2025, 12, 31)

        delta = (end - start).days
        if delta <= 0:
            delta = 365

        return [start + timedelta(days=random.randint(0, delta)) for _ in range(count)]

    def _gen_random_string(self, config: dict, count: int) -> list:
        """Generate random strings of specified length range."""
        min_len = config.get("min_length", 5)
        max_len = config.get("max_length", 20)
        return [
            "".join(random.choices(string.ascii_letters, k=random.randint(min_len, max_len)))
            for _ in range(count)
        ]

    # ── Multi-table generation with referential integrity ───────────────────────

    def generate_multi_table(
        self,
        schemas: list[dict],
        rules_map: dict,
        relationships: list[dict],
        row_counts: dict,
        scenario_overrides: Optional[dict] = None,
    ) -> dict[str, pd.DataFrame]:
        """
        Generate data for multiple related tables, preserving referential integrity.
        
        Args:
            schemas: List of schema dicts.
            rules_map: Dict of table_name → list of rules.
            relationships: List of FK relationships.
            row_counts: Dict of table_name → row count.
            scenario_overrides: Optional dict of table.column → override config.
        """
        generated = {}

        # Build dependency order (topological sort by FK)
        dependency_graph = {s["table_name"]: set() for s in schemas}
        for rel in relationships:
            from_table = rel["from_table"]
            to_table = rel["to_table"]
            if from_table in dependency_graph:
                dependency_graph[from_table].add(to_table)

        order = self._topological_sort(dependency_graph)

        for table_name in order:
            schema = next((s for s in schemas if s["table_name"] == table_name), None)
            if not schema:
                continue

            table_rules = rules_map.get(table_name, [])
            count = row_counts.get(table_name, 1000)

            # Generate base data
            overrides = None
            if scenario_overrides and table_name in scenario_overrides:
                overrides = scenario_overrides[table_name]

            df = self.generate(schema, table_rules, count, overrides)

            # Patch FK columns with valid references
            for rel in relationships:
                if rel["from_table"] == table_name and rel["to_table"] in generated:
                    ref_df = generated[rel["to_table"]]
                    ref_col = rel["to_column"]
                    from_col = rel["from_column"]

                    if ref_col in ref_df.columns and from_col in df.columns:
                        valid_ids = ref_df[ref_col].dropna().tolist()
                        if valid_ids:
                            df[from_col] = [random.choice(valid_ids) for _ in range(len(df))]

            generated[table_name] = df

        return generated

    def _topological_sort(self, graph: dict) -> list:
        """Simple topological sort for dependency resolution."""
        visited = set()
        order = []

        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, set()):
                dfs(dep)
            order.append(node)

        for node in graph:
            dfs(node)

        return order
