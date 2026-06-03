# Cortex MCP Server

Cortex/Neurex test-otomasyon motorunu **Model Context Protocol** üzerinden dış AI
agent'lara (Cursor, Claude Desktop, vb.) açar. Octomind MCP server muadili.

## Sunulan tool'lar

| Tool | İş |
|------|----|
| `discover_tests(url, max_pages, max_flows)` | Siteyi otonom keşfet → çalıştırılabilir testler üret |
| `crawl_site(url, max_pages)` | Sadece sayfa yapısı keşfi |
| `analyze_test_failure(test_name, error_message, ...)` | Başarısızlığın kök neden analizi |
| `generate_tests_from_requirement(text, title)` | Gereksinim/PRD metninden test üret |
| `jira_issue_to_tests(issue_key)` | Jira ticket'ından test üret |
| `heal_locator(url, fingerprint)` | Kırılan locator'ı çok-sinyalli iyileştir |
| `capabilities()` | Tüm yeteneklerin sağlık durumu |

## Kurulum

```bash
cd mcp_server
python -m venv .venv && source .venv/bin/activate   # Python 3.10+
pip install -r requirements.txt
```

## Çalıştırma

Engine'in çalışıyor olması gerekir (varsayılan `http://localhost:5001`).

```bash
export CORTEX_ENGINE_URL=http://localhost:5001
export CORTEX_INTERNAL_KEY=<engine ENGINE_INTERNAL_KEY değeri>
python cortex_mcp.py          # stdio transport
```

## İstemci yapılandırması

### Claude Desktop / Cursor (`mcp.json` veya `claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["/abs/path/to/Cortex_Ai_Automation/mcp_server/cortex_mcp.py"],
      "env": {
        "CORTEX_ENGINE_URL": "http://localhost:5001",
        "CORTEX_INTERNAL_KEY": "<engine internal key>"
      }
    }
  }
}
```

Yeniden başlattıktan sonra agent'a şunları diyebilirsiniz:
> "saucedemo.com'u keşfet ve login akışı için test üret"
> "Bu testi neden fail etti analiz et: TimeoutError waiting for #submit"

## Not

Bu süreç **kullanıcının makinesinde** çalışır ve engine HTTP API'sine
`X-Internal-Key` ile proxy yapar; engine container'ının içinde çalışmaz.
Engine'in `/api/discovery`, `/api/rca`, `/api/connectors`, `/api/self-heal`
endpoint'lerini kullanır (Dalga: rakip-paritesi özellikleri).
