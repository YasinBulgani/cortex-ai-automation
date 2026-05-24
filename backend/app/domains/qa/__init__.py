"""qa/ domain — git-native test management REST API.

`qa/` klasöründeki test artifact'leri (cases, plans, runs, requirements,
defects, coverage, health) REST endpoint olarak expose eder. Frontend
(`apps/web/app/(dashboard)/qa/`) ve external automation/bot script'ler
bu API'yi kullanır.

Veri kaynağı: repo'daki `qa/` klasörü (filesystem). State değiştiren
endpoint'ler (POST run, PATCH TC) dosyaya yazar; CI bot bunları commit eder.
"""
