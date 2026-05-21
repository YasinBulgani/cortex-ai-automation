#!/usr/bin/env node

/**
 * Paribu Test Otomasyon Framework için Kapsamlı Test Runner
 * 
 * Bu script, çeşitli seçeneklerle test çalıştırmak için birleşik bir arayüz sağlar:
 * - Tüm testleri veya tag'lere göre filtrelenmiş testleri çalıştır
 * - Belirli tarayıcılarda çalıştır
 * - Belirli ortamlarda çalıştır
 * - Paralel çalıştırma
 * - Rapor oluşturma
 * - Özel yapılandırmalar
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';
import * as fs from 'fs';

const execAsync = promisify(exec);

interface TestRunnerOptions {
  tags?: string[];
  browser?: 'chromium' | 'firefox' | 'webkit';
  environment?: 'qa' | 'stage' | 'prod' | 'paribu';
  parallel?: number;
  headless?: boolean;
  generateReport?: boolean;
  verbose?: boolean;
  timeout?: number;
}

class TestRunner {
  private options: TestRunnerOptions;

  constructor(options: TestRunnerOptions = {}) {
    this.options = {
      tags: options.tags || [],
      browser: options.browser,
      environment: options.environment,
      parallel: options.parallel,
      headless: options.headless !== false,
      generateReport: options.generateReport !== false,
      verbose: options.verbose || false,
      timeout: options.timeout || 60000
    };
  }

  /**
   * Tüm seçeneklerle Cucumber komutunu oluştur
   */
  private buildCucumberCommand(): string {
    const args: string[] = [];

    // Belirtilmişse tag'leri ekle
    if (this.options.tags && this.options.tags.length > 0) {
      const tagExpression = this.options.tags.join(' and ');
      args.push('--tags', tagExpression);
    }

    // World parametrelerini ekle
    const worldParams: any = {};
    if (this.options.browser) {
      worldParams.browser = this.options.browser;
    }
    if (this.options.environment) {
      worldParams.environment = this.options.environment;
    }
    if (this.options.headless !== undefined) {
      worldParams.headless = this.options.headless;
    }
    
    if (Object.keys(worldParams).length > 0) {
      args.push('--world-parameters', JSON.stringify(worldParams));
    }

    // Paralel çalıştırmayı ekle
    if (this.options.parallel && this.options.parallel > 1) {
      args.push('--parallel', this.options.parallel.toString());
    }

    // Format seçeneklerini ekle
    args.push('--format', 'progress-bar');
    args.push('--format', 'json:reports/cucumber-report.json');
    args.push('--format', 'html:reports/cucumber-report.html');
    args.push('--format', '@cucumber/pretty-formatter');

    // Timeout ekle
    if (this.options.timeout) {
      args.push('--timeout', this.options.timeout.toString());
    }

    return `cucumber-js ${args.join(' ')}`;
  }

  /**
   * Raporlar dizininin var olduğundan emin ol
   */
  private ensureReportsDirectory(): void {
    const reportsDir = path.join(process.cwd(), 'reports');
    const screenshotsDir = path.join(reportsDir, 'screenshots');
    
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }
  }

  /**
   * HTML raporu oluştur
   */
  private async generateReport(): Promise<void> {
    if (!this.options.generateReport) {
      return;
    }

    try {
      const reportScript = path.join(process.cwd(), 'utils', 'generate-report.js');
      const { stdout, stderr } = await execAsync(`node ${reportScript}`);
      
      if (stdout) {
        console.log(stdout);
      }
      if (stderr && !stderr.includes('Warning')) {
        console.error('Rapor uyarıları:', stderr);
      }
      
      console.log('\n✅ HTML raporu oluşturuldu: reports/cucumber_report.html');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('❌ Rapor oluşturma başarısız:', errorMessage);
    }
  }

  /**
   * Testleri çalıştır
   */
  async run(): Promise<{ success: boolean; exitCode: number }> {
    try {
      console.log('🚀 Test Çalıştırması Başlatılıyor...\n');
      
      // Yapılandırmayı göster
      this.displayConfiguration();

      // Raporlar dizininin var olduğundan emin ol
      this.ensureReportsDirectory();

      // Komutu oluştur ve çalıştır
      const command = this.buildCucumberCommand();
      
      if (this.options.verbose) {
        console.log(`📝 Komut: ${command}\n`);
      }

      const { stdout, stderr } = await execAsync(command, {
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer
        env: {
          ...process.env,
          HEADLESS: this.options.headless ? 'true' : 'false',
          ENVIRONMENT: this.options.environment || process.env.ENVIRONMENT || 'qa'
        }
      });

      if (stdout) {
        console.log(stdout);
      }
      if (stderr && !stderr.includes('Warning')) {
        console.error(stderr);
      }

      // Rapor oluştur
      await this.generateReport();

      console.log('\n✅ Test çalıştırması başarıyla tamamlandı!');
      return { success: true, exitCode: 0 };

    } catch (error: unknown) {
      console.error('\n❌ Test çalıştırması başarısız oldu!');
      
      if (error instanceof Error) {
      console.error('Hata:', error.message);
      } else {
        console.error('Hata:', String(error));
      }
      
      if (error && typeof error === 'object' && 'stdout' in error) {
        console.log('Çıktı:', (error as { stdout: string }).stdout);
      }
      if (error && typeof error === 'object' && 'stderr' in error) {
        console.error('Hatalar:', (error as { stderr: string }).stderr);
      }

      // Yine de rapor oluşturmayı dene
      await this.generateReport();

      const exitCode = error && typeof error === 'object' && 'code' in error 
        ? (error as { code: number }).code 
        : 1;
      return { success: false, exitCode };
    }
  }

  /**
   * Mevcut yapılandırmayı göster
   */
  private displayConfiguration(): void {
    console.log('📋 Test Yapılandırması:');
    console.log('─'.repeat(50));
    
    if (this.options.tags && this.options.tags.length > 0) {
      console.log(`  Tag'ler: ${this.options.tags.join(', ')}`);
    } else {
      console.log('  Tag'ler: Tüm testler');
    }
    
    if (this.options.browser) {
      console.log(`  Tarayıcı: ${this.options.browser}`);
    } else {
      console.log('  Tarayıcı: Varsayılan (chromium)');
    }
    
    if (this.options.environment) {
      console.log(`  Ortam: ${this.options.environment}`);
    } else {
      console.log('  Ortam: Varsayılan (qa)');
    }
    
    if (this.options.parallel && this.options.parallel > 1) {
      console.log(`  Paralel Worker: ${this.options.parallel}`);
    } else {
      console.log('  Paralel Worker: Sıralı');
    }
    
    console.log(`  Headless: ${this.options.headless ? 'Evet' : 'Hayır'}`);
    console.log(`  Timeout: ${this.options.timeout}ms`);
    console.log(`  Rapor Oluştur: ${this.options.generateReport ? 'Evet' : 'Hayır'}`);
    console.log('─'.repeat(50));
    console.log('');
  }
}

// CLI Arayüzü
if (require.main === module) {
  const args = process.argv.slice(2);
  const options: TestRunnerOptions = {};

  // Komut satırı argümanlarını parse et
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    switch (arg) {
      case '--tags':
      case '-t':
        const tags = args[++i]?.split(',').map(t => t.trim()) || [];
        options.tags = tags;
        break;
      
      case '--browser':
      case '-b':
        const browser = args[++i] as 'chromium' | 'firefox' | 'webkit';
        if (['chromium', 'firefox', 'webkit'].includes(browser)) {
          options.browser = browser;
        }
        break;
      
      case '--env':
      case '-e':
        const env = args[++i] as 'qa' | 'stage' | 'prod' | 'paribu';
        if (['qa', 'stage', 'prod', 'paribu'].includes(env)) {
          options.environment = env;
        }
        break;
      
      case '--parallel':
      case '-p':
        const workers = parseInt(args[++i] || '4', 10);
        options.parallel = workers > 0 ? workers : 4;
        break;
      
      case '--headless':
        options.headless = true;
        break;
      
      case '--headed':
        options.headless = false;
        break;
      
      case '--no-report':
        options.generateReport = false;
        break;
      
      case '--verbose':
      case '-v':
        options.verbose = true;
        break;
      
      case '--timeout':
        const timeout = parseInt(args[++i] || '60000', 10);
        options.timeout = timeout;
        break;
      
      case '--help':
      case '-h':
        console.log(`
Test Runner Kullanımı:

  npm run test:runner [seçenekler]

Seçenekler:
  --tags, -t <tag'ler>          Virgülle ayrılmış tag'ler (örn: "@api,@login")
  --browser, -b <tarayıcı>      Tarayıcı: chromium, firefox, webkit
  --env, -e <ortam>             Ortam: qa, stage, prod, paribu
  --parallel, -p <worker>       Paralel worker sayısı (varsayılan: 4)
  --headless                     Headless modda çalıştır
  --headed                       Headed modda çalıştır (varsayılan)
  --no-report                    Rapor oluşturmayı atla
  --verbose, -v                  Detaylı çıktı
  --timeout <ms>                 Test timeout milisaniye cinsinden (varsayılan: 60000)
  --help, -h                     Bu yardım mesajını göster

Örnekler:
  npm run test:runner -- --tags @api
  npm run test:runner -- --tags @web --browser firefox
  npm run test:runner -- --env paribu --parallel 4
  npm run test:runner -- --tags @api,@login --headless
        `);
        process.exit(0);
    }
  }

  // Testleri çalıştır
  const runner = new TestRunner(options);
  runner.run().then(result => {
    process.exit(result.exitCode);
  }).catch(error => {
    console.error('Kritik hata:', error);
    process.exit(1);
  });
}

export { TestRunner, TestRunnerOptions };

