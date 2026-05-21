"""DSL Sözlüğü — packages/dsl/catalog altındaki test cümleciklerini HTTP üzerinden sunar.

Alt modüller doğrudan `from app.domains.dsl.router import router` gibi
import edilir; bu `__init__.py` kasıtlı olarak hafif tutulmuştur — böylece
`loader`'ı standalone import ederken (ör. CLI, migration script'leri) HTTP
katmanı + DB bağımlılıkları zorla yüklenmek zorunda kalmaz.
"""
