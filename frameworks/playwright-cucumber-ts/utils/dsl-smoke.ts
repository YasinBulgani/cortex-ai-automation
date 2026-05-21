/**
 * DSL loader smoke test — cucumber-js runtime gerektirmez, sadece
 * YAML okuma ve kategorizasyon tarafını test eder.
 *
 * Çalıştırma:
 *   cd frameworks/playwright-cucumber-ts
 *   npx ts-node --transpile-only utils/dsl-smoke.ts
 */
import { loadActions } from '../../../packages/dsl/loaders/typescript/catalogLoader';

const actions = loadActions();
console.log(`Toplam action: ${actions.length}`);

const byCategory: Record<string, number> = {};
for (const a of actions) {
  const top = (a.category || '').split('.')[0] || '?';
  byCategory[top] = (byCategory[top] ?? 0) + 1;
}
console.log('Kategori dağılımı:', byCategory);

const tsOnly = actions.filter((a) => a.implementations?.typescript);
console.log(`TypeScript implementasyonu olan: ${tsOnly.length}`);
if (tsOnly.length > 0) {
  const sample = tsOnly[0];
  console.log('Örnek:', {
    id: sample.id,
    category: sample.category,
    langs: Object.keys(sample.aliases || {}),
    ts_impl_keys: Object.keys(sample.implementations?.typescript ?? {}),
  });
}
