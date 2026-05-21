import { readFileSync } from 'node:fs';
import { globSync } from 'node:fs';

export interface BDDGenerationConfig {
  existingStepDefs: string;
  existingFeatures: string;
  language: 'tr' | 'en';
  maxScenariosPerStory: number;
}

export interface GeneratedFeature {
  featureName: string;
  content: string;
  scenarioCount: number;
  reusedSteps: string[];
  newStepsNeeded: string[];
}

const DEFAULT_CONFIG: BDDGenerationConfig = {
  existingStepDefs: 'engine/steps/**/*.py',
  existingFeatures: 'engine/features/**/*.feature',
  language: 'tr',
  maxScenariosPerStory: 10,
};

/**
 * Mevcut step definition'ları dosyalardan çıkarır.
 */
export function extractExistingSteps(globPattern: string): string[] {
  const steps: string[] = [];
  try {
    const { globSync: gs } = require('glob');
    const files: string[] = gs(globPattern);
    for (const file of files) {
      const content = readFileSync(file, 'utf-8');
      const matches = content.match(/@(given|when|then|step)\(\s*['"](.+?)['"]\s*\)/gi) ?? [];
      steps.push(...matches);
    }
  } catch {
    // glob bulunamazsa boş döner
  }
  return steps;
}

/**
 * User story'den BDD senaryosu üretmek için LLM prompt'u oluşturur.
 */
export function buildBDDPrompt(
  userStory: string,
  existingSteps: string[],
  config: BDDGenerationConfig = DEFAULT_CONFIG,
): string {
  const langInstructions = config.language === 'tr'
    ? 'Türkçe Gherkin anahtar kelimeleri kullan: Özellik, Senaryo, Senaryo Taslağı, Diyelim ki, Ve, Eğer, O zaman, Örnekler'
    : 'Use English Gherkin keywords: Feature, Scenario, Scenario Outline, Given, When, Then, Examples';

  return `
Sen bir BDD uzmanısın. Aşağıdaki user story'den Gherkin senaryoları üret.

## Dil:
${langInstructions}

## Mevcut Step Definition'lar (mümkün olduğunca tekrar kullan):
${existingSteps.slice(0, 50).join('\n') || '(henüz mevcut step yok)'}

## User Story:
${userStory}

## Kurallar:
1. Her senaryo bağımsız ve izole olmalı
2. Happy path + en az 2 negative path üret
3. Mevcut step'leri mümkün olduğunca tekrar kullan
4. Yeni step gerekiyorsa sonuna # YENİ_STEP yorumu ekle
5. Scenario Outline + Examples kullan (veri çeşitliliği)
6. Tag'ler: @smoke, @regression, @negative, @e2e, @critical
7. Maksimum ${config.maxScenariosPerStory} senaryo üret
8. Edge case'leri kapsa (boş veri, sınır değerler, yetkisiz erişim)

Sadece .feature dosya içeriği üret, açıklama yazma.
`.trim();
}

export function parseFeatureContent(raw: string): GeneratedFeature {
  const featureMatch = raw.match(/(?:Feature|Özellik):\s*(.+)/);
  const scenarioMatches = raw.match(/(?:Scenario|Senaryo|Scenario Outline|Senaryo Taslağı):/g) ?? [];
  const newSteps = (raw.match(/#\s*YENİ_STEP.*/g) ?? []).map(s => s.replace(/#\s*YENİ_STEP\s*/, '').trim());

  return {
    featureName: featureMatch?.[1]?.trim() ?? 'Generated Feature',
    content: raw,
    scenarioCount: scenarioMatches.length,
    reusedSteps: [],
    newStepsNeeded: newSteps,
  };
}
