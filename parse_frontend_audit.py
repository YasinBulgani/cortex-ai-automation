#!/usr/bin/env python3
import json
import re
import csv
import sys
from pathlib import Path

# Read the workflow output
output_file = Path('/Users/yasin_bulgan/.claude/projects/-Users-yasin-bulgan-Desktop-Cortex-Ai-Automation/a692def8-a378-4bf1-9d05-c36efcc7d4b0/tool-results/b0ifd7hh6.txt')

with open(output_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract JSON from the output
json_match = re.search(r'\{[\s\S]*\}', content)
if not json_match:
    print("❌ JSON bulunamadı")
    sys.exit(1)

try:
    data = json.loads(json_match.group())
except json.JSONDecodeError as e:
    print(f"❌ JSON parse error: {e}")
    sys.exit(1)

reports = data.get('result', {}).get('reports', {})

all_findings = []

# Parse each report
for report_type, report_text in reports.items():
    if not isinstance(report_text, str):
        continue

    # Extract JSON array from markdown code blocks
    json_arrays = re.findall(r'\[[\s\S]*?\](?=\n```)', report_text)
    if not json_arrays:
        json_arrays = re.findall(r'\[[\s\S]*?\]', report_text)

    for json_str in json_arrays:
        try:
            findings = json.loads(json_str)
            if isinstance(findings, list):
                for finding in findings:
                    finding['_report_type'] = report_type
                    all_findings.append(finding)
                break
        except json.JSONDecodeError:
            continue

print(f"✅ Toplam {len(all_findings)} bulgu tespit edildi\n")

# Categorize by severity
critical = [f for f in all_findings if f.get('severite') == 'Kritik']
high = [f for f in all_findings if f.get('severite') == 'Yüksek']
medium = [f for f in all_findings if f.get('severite') == 'Orta']
low = [f for f in all_findings if f.get('severite') == 'Düşük']

print(f"🔴 Kritik: {len(critical)}")
print(f"🟠 Yüksek: {len(high)}")
print(f"🟡 Orta: {len(medium)}")
print(f"🟢 Düşük: {len(low)}\n")

# Write CSV
output_csv = Path('/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/project_frontend_analiz_bulgulari.csv')

# Determine all unique keys from findings
all_keys = set()
for finding in all_findings:
    all_keys.update(finding.keys())

# Standard order for CSV columns
column_order = [
    'id', 'dosya', 'ekran', 'özellik', 'başlık', 'kategori', 'severite',
    'mevcut', 'problem', 'çözüm', 'kullanıcıEtkisi', 'tasarımÖnerisi',
    'impact', 'gereksinim', 'testAlanları', 'testSenaryosu', 'otomasyonUygun',
    'eforSeviyesi', '_report_type'
]

# Add any missing keys
all_keys.update(column_order)
columns = [col for col in column_order if col in all_keys or col.startswith('_')]
if 'satır' in all_keys:
    columns.insert(columns.index('dosya')+1, 'satır')

with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()

    for finding in all_findings:
        row = {col: finding.get(col, '') for col in columns}
        writer.writerow(row)

print(f"📄 CSV kaydedildi: {output_csv}")
print(f"   Satır sayısı: {len(all_findings)}")
print(f"   Sütun sayısı: {len(columns)}")
