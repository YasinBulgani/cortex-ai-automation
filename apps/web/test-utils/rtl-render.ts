/**
 * Test render shim — @testing-library/react'in `render`'ını otomatik olarak
 * QueryClientProvider ile sarar. jest.config.js moduleNameMapper üzerinden
 * `@testing-library/react` importları buraya yönlendirilir.
 *
 * Neden: 100 test dosyasının çoğu, TanStack Query kullanan bileşenleri
 * provider'sız render ediyordu → "No QueryClient set" (370 fail'in ~294'ü).
 *
 * Önemli: spread/Proxy, RTL'in non-enumerable export'larını (örn. `act`)
 * kaybediyor → getOwnPropertyDescriptors ile TÜM descriptor'lar (getter dahil)
 * kopyalanır ve __esModule açıkça korunur, böylece `import { act, screen }`
 * interop'u çalışır. Gerçek RTL jest.requireActual ile alınır.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
const React = require("react");
// react-query BARE require ile alınır → component'lerin kullandığı AYNI modül
// örneği olur; aksi halde Provider context'i useQuery context'iyle eşleşmez.
// (Relative path ayrı örnek yaratıp "No QueryClient" hatasını geri getirir.)
const RQ = require("@tanstack/react-query");

// ÖNEMLİ: jest moduleNameMapper, requireActual'ı da yakalar → bare specifier
// kullanırsak bu shim kendini rekürsif require eder ve `act` gibi export'lar
// kaybolur. Gerçek RTL'i, mapper'ın yakalamadığı relative path ile alıyoruz
// (monorepo: root node_modules'a hoist; shim apps/web/test-utils/ altında).
const actual: any = require("../../../node_modules/@testing-library/react");

function render(ui: any, options: any = {}) {
  // react-query mock'lanmış olabilir (jest.mock) → QueryClient constructor
  // olmaz. O testlerde hook'lar da mock; provider gereksiz → plain render.
  let client: any;
  try {
    client = new RQ.QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0, staleTime: 0 },
        mutations: { retry: false },
      },
    });
  } catch {
    return actual.render(ui, options);
  }
  // react-query jest.fn() ile mock'lanmışsa client gerçek değildir (constructor
  // patlamaz ama getQueryCache yoktur) → sarma, çift provider/testid olmasın.
  if (!client || typeof client.getQueryCache !== "function") {
    return actual.render(ui, options);
  }
  const InnerWrapper = options.wrapper;
  const rest = { ...options };
  delete rest.wrapper;
  const Wrapper = ({ children }: any) =>
    React.createElement(
      RQ.QueryClientProvider,
      { client },
      InnerWrapper ? React.createElement(InnerWrapper, null, children) : children,
    );
  return actual.render(ui, { wrapper: Wrapper, ...rest });
}

// Tüm RTL export'larını descriptor seviyesinde kopyala (getter/non-enumerable
// dahil — `act` bu yüzden kayboluyordu), sonra render'ı override et.
// render/__esModule non-configurable kopyalanıp redefine'ı engellememesi için
// descriptor setinden çıkar; gerisini (getter'lar, act dahil) aynen kopyala.
const descriptors: any = Object.getOwnPropertyDescriptors(actual);
delete descriptors.render;
delete descriptors.__esModule;
const shim: any = {};
Object.defineProperties(shim, descriptors);
Object.defineProperty(shim, "render", { value: render, enumerable: true });
Object.defineProperty(shim, "__esModule", { value: true });

module.exports = shim;
