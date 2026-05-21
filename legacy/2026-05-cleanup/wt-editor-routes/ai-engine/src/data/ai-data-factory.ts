import { faker } from '@faker-js/faker/locale/tr';

export interface Employee {
  tcKimlik: string;
  ad: string;
  soyad: string;
  email: string;
  telefon: string;
  departman: string;
  unvan: string;
  iseGirisTarihi: string;
  sicilNo: string;
  aktif: boolean;
}

const DEPARTMENTS = ['Yazılım', 'İnsan Kaynakları', 'Finans', 'Operasyon', 'Satış', 'Hukuk', 'Kalite'] as const;
const TITLES = ['Uzman', 'Kıdemli Uzman', 'Müdür', 'Direktör', 'Teknisyen', 'Analist', 'Koordinatör'] as const;

export class AIDataFactory {
  /**
   * Algoritmik olarak geçerli bir TC Kimlik No üretir (sentetik).
   * Gerçek bir kişiye ait değildir.
   */
  generateTCKimlik(): string {
    const d = Array.from({ length: 9 }, (_, i) =>
      i === 0 ? faker.number.int({ min: 1, max: 9 }) : faker.number.int({ min: 0, max: 9 }),
    );
    const d10 = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10;
    d.push(d10 < 0 ? d10 + 10 : d10);
    d.push(d.reduce((a, b) => a + b, 0) % 10);
    return d.join('');
  }

  generateEmployee(overrides: Partial<Employee> = {}): Employee {
    const ad = faker.person.firstName();
    const soyad = faker.person.lastName();
    return {
      tcKimlik: this.generateTCKimlik(),
      ad,
      soyad,
      email: faker.internet.email({ firstName: ad, lastName: soyad, provider: 'bgts.com.tr' }),
      telefon: faker.phone.number({ style: 'national' }),
      departman: faker.helpers.arrayElement([...DEPARTMENTS]),
      unvan: faker.helpers.arrayElement([...TITLES]),
      iseGirisTarihi: faker.date.between({ from: '2015-01-01', to: '2026-01-01' }).toISOString().split('T')[0],
      sicilNo: faker.string.numeric(6),
      aktif: true,
      ...overrides,
    };
  }

  generateBulk(count: number, overrides: Partial<Employee> = {}): Employee[] {
    return Array.from({ length: count }, () => this.generateEmployee(overrides));
  }

  /**
   * Senaryo bazlı test veri seti üretimi.
   * Her senaryo, o senaryoya özel veriler içerir.
   */
  generateForScenario(scenario: string): Record<string, unknown> {
    const generators: Record<string, () => Record<string, unknown>> = {
      'login-valid': () => ({
        user: this.generateEmployee({ aktif: true }),
        password: 'ValidPass123!',
        expectedResult: 'success',
      }),
      'login-invalid': () => ({
        user: this.generateEmployee({ aktif: true }),
        password: 'wrong',
        expectedResult: 'error',
        expectedMessage: 'Geçersiz kullanıcı adı veya şifre',
      }),
      'login-locked': () => ({
        user: this.generateEmployee({ aktif: false }),
        password: 'ValidPass123!',
        expectedResult: 'locked',
        expectedMessage: 'Hesabınız kilitlenmiştir',
      }),
      'bulk-import': () => ({
        employees: this.generateBulk(100),
        expectedImportCount: 100,
        expectedErrors: 0,
      }),
      'search-filter': () => ({
        employees: this.generateBulk(50),
        searchTerm: faker.person.firstName(),
        filterDepartment: faker.helpers.arrayElement([...DEPARTMENTS]),
      }),
    };

    const gen = generators[scenario];
    if (!gen) throw new Error(`Bilinmeyen senaryo: ${scenario}`);
    return gen();
  }
}

export const dataFactory = new AIDataFactory();
