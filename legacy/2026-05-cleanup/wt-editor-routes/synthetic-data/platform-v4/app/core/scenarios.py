"""
Banking Scenarios — predefined scenario profiles that override generation rules
to produce realistic, domain-specific datasets.
"""


# ── Predefined Banking Scenarios ───────────────────────────────────────────────
SCENARIOS = {
    "default": {
        "name": "Varsayılan",
        "name_en": "Default",
        "description": "Standart dağılımlarla veri üretimi — kurallar olduğu gibi uygulanır.",
        "icon": "📊",
        "overrides": {},
    },

    "premium_customer": {
        "name": "Premium Müşteri",
        "name_en": "Premium Customer",
        "description": "Yüksek bakiyeli, çoklu ürünlere sahip, uzun süreli VIP müşteriler.",
        "icon": "💎",
        "overrides": {
            "customers": {
                "balance": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 100000, "max": 5000000,
                        "distribution": "normal", "mean": 1500000, "std": 500000
                    }
                },
                "segment": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["VIP", "Premium", "Platinum"], "weights": [0.3, 0.4, 0.3]}
                },
                "credit_score": {
                    "rule_type": "range",
                    "rule_config": {"min": 750, "max": 1000, "distribution": "normal", "mean": 850, "std": 50}
                },
                "status": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["active"], "weights": [1.0]}
                },
            },
            "accounts": {
                "balance": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 50000, "max": 2000000,
                        "distribution": "normal", "mean": 500000, "std": 200000
                    }
                },
                "account_type": {
                    "rule_type": "enum",
                    "rule_config": {
                        "values": ["Yatırım", "Vadeli Mevduat", "Altın Hesap", "Döviz"],
                        "weights": [0.3, 0.3, 0.2, 0.2]
                    }
                },
            },
            "transactions": {
                "amount": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 1000, "max": 500000,
                        "distribution": "normal", "mean": 50000, "std": 30000
                    }
                },
            },
        },
    },

    "new_customer": {
        "name": "Yeni Müşteri",
        "name_en": "New Customer",
        "description": "Son 6 ayda katılmış, tek hesaplı, düşük-orta bakiyeli müşteriler.",
        "icon": "🆕",
        "overrides": {
            "customers": {
                "balance": {
                    "rule_type": "range",
                    "rule_config": {"min": 0, "max": 50000, "distribution": "uniform"}
                },
                "segment": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["Standard", "Basic"], "weights": [0.6, 0.4]}
                },
                "credit_score": {
                    "rule_type": "range",
                    "rule_config": {"min": 300, "max": 600, "distribution": "uniform"}
                },
            },
            "accounts": {
                "balance": {
                    "rule_type": "range",
                    "rule_config": {"min": 0, "max": 25000, "distribution": "uniform"}
                },
                "account_type": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["Vadesiz", "Tasarruf"], "weights": [0.7, 0.3]}
                },
            },
        },
    },

    "high_risk": {
        "name": "Yüksek Riskli",
        "name_en": "High Risk",
        "description": "Gecikmiş ödemeleri olan, düşük kredi skorlu, potansiyel temerrüt müşterileri.",
        "icon": "⚠️",
        "overrides": {
            "customers": {
                "credit_score": {
                    "rule_type": "range",
                    "rule_config": {"min": 100, "max": 400, "distribution": "normal", "mean": 250, "std": 60}
                },
                "segment": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["Risk", "Collection"], "weights": [0.6, 0.4]}
                },
                "status": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["active", "frozen", "suspended"], "weights": [0.3, 0.4, 0.3]}
                },
            },
            "accounts": {
                "balance": {
                    "rule_type": "range",
                    "rule_config": {"min": -50000, "max": 5000, "distribution": "normal", "mean": -10000, "std": 15000}
                },
            },
            "transactions": {
                "amount": {
                    "rule_type": "range",
                    "rule_config": {"min": 10, "max": 5000, "distribution": "uniform"}
                },
                "type": {
                    "rule_type": "enum",
                    "rule_config": {
                        "values": ["gecikme_faizi", "tahsilat", "icra", "odeme"],
                        "weights": [0.3, 0.3, 0.2, 0.2]
                    }
                },
            },
        },
    },

    "corporate": {
        "name": "Kurumsal",
        "name_en": "Corporate",
        "description": "Şirket hesapları, yüksek hacimli işlemler, ticari ürünler.",
        "icon": "🏢",
        "overrides": {
            "customers": {
                "full_name": {
                    "rule_type": "faker",
                    "rule_config": {"provider": "company", "locale": "tr_TR"}
                },
                "balance": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 500000, "max": 50000000,
                        "distribution": "normal", "mean": 10000000, "std": 5000000
                    }
                },
                "segment": {
                    "rule_type": "enum",
                    "rule_config": {"values": ["Corporate", "Enterprise", "SME"], "weights": [0.4, 0.3, 0.3]}
                },
            },
            "accounts": {
                "account_type": {
                    "rule_type": "enum",
                    "rule_config": {
                        "values": ["Ticari Hesap", "Dış Ticaret", "Akreditif", "Yatırım"],
                        "weights": [0.4, 0.25, 0.15, 0.2]
                    }
                },
                "balance": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 100000, "max": 20000000,
                        "distribution": "normal", "mean": 5000000, "std": 3000000
                    }
                },
            },
            "transactions": {
                "amount": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 10000, "max": 5000000,
                        "distribution": "normal", "mean": 500000, "std": 300000
                    }
                },
            },
        },
    },

    "fraud_test": {
        "name": "Dolandırıcılık Test",
        "name_en": "Fraud Testing",
        "description": "Anormal işlem kalıpları ile dolandırıcılık algılama testleri için veri.",
        "icon": "🔍",
        "overrides": {
            "transactions": {
                "amount": {
                    "rule_type": "range",
                    "rule_config": {
                        "min": 1, "max": 10000000,
                        "distribution": "normal", "mean": 250000, "std": 500000
                    }
                },
                "type": {
                    "rule_type": "enum",
                    "rule_config": {
                        "values": ["transfer", "withdrawal", "online_purchase", "international"],
                        "weights": [0.2, 0.2, 0.3, 0.3]
                    }
                },
            },
        },
    },
}


class ScenarioManager:
    """Manages and applies banking scenarios to data generation."""

    def list_scenarios(self) -> list[dict]:
        """Return a summary list of all available scenarios."""
        return [
            {
                "key": key,
                "name": s["name"],
                "name_en": s["name_en"],
                "description": s["description"],
                "icon": s["icon"],
            }
            for key, s in SCENARIOS.items()
        ]

    def get_scenario(self, key: str) -> dict | None:
        """Get a specific scenario by key."""
        return SCENARIOS.get(key)

    def get_overrides(self, key: str, table_name: str) -> dict | None:
        """Get column overrides for a specific table within a scenario."""
        scenario = SCENARIOS.get(key)
        if not scenario:
            return None
        return scenario.get("overrides", {}).get(table_name)

    def apply_scenario(self, key: str, rules: list[dict], table_name: str) -> list[dict]:
        """
        Apply scenario overrides to existing rules.
        Override rules replace matching column rules.
        """
        overrides = self.get_overrides(key, table_name)
        if not overrides:
            return rules

        # Build override map
        override_cols = set(overrides.keys())

        # Filter out overridden rules, keep the rest
        new_rules = [r for r in rules if r["column_name"] not in override_cols]

        # Add override rules
        for col_name, override in overrides.items():
            new_rules.append({
                "column_name": col_name,
                **override,
            })

        return new_rules
