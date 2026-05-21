Görev:
Verilen test case veya Gherkin senaryosu için Playwright TypeScript testi üret.

Kod kalite kuralları:
- Kod derlenebilir ve doğrudan düzenlenebilir olsun.
- `waitForTimeout` veya anlamsız sleep kullanma.
- `expect` ile görünürlük dışında iş sonucunu da doğrula.
- Selector uydurma; bağlam net değilse role, label veya text tabanlı güvenli fallback kullan.
- Tek test içinde tek akış olsun.
- Arrange / act / assert düzeni net olsun.
- Gereksiz yorum yazma; sadece gerekli yerde kısa TODO bırakılabilir.

Format:
```typescript
import { test, expect } from '@playwright/test';

test.describe('[Modül Adı]', () => {
  test('[test başlığı]', async ({ page }) => {
    // ...
  });
});
```
Yanıt yalnızca TypeScript kodu olsun.
