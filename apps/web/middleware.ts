/**
 * Next.js Edge Middleware — sunucu tarafı rota koruması.
 *
 * Amaç: Login olmamış kullanıcı korumalı sayfalara gittiğinde tarayıcıda
 * React hydrate olana kadar geçen sürede "yetkisiz içerik flash" yaşamasını
 * önler ve URL'i doğrudan bilen birine bile login ekranını gösterir.
 *
 * Bu katman **yetkilendirme doğrulaması yapmaz** — token imzasının gerçek
 * kontrolü FastAPI katmanında `Depends(get_current_user)` ile olur.
 * Middleware yalnızca `twai_session` presence cookie'sine bakar.
 *
 * Feature flag ile kapatılabilir:
 *   NEXT_PUBLIC_AUTH_MIDDLEWARE_ENABLED=false
 */

import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "twai_session";

const PUBLIC_PATHS: RegExp[] = [
  /^\/login(\/|$)/,
  /^\/reset-password(\/|$)/,
  /^\/forgot-password(\/|$)/,
  /^\/terms(\/|$)/,
  /^\/privacy(\/|$)/,
  /^\/api\//,
  /^\/_next\//,
  /^\/favicon\.ico$/,
  /^\/assets\//,
  /^\/public\//,
  /^\/robots\.txt$/,
  /^\/sitemap\.xml$/,
  // PWA assets
  /^\/manifest\.json$/,
  /^\/icon-\d+\.(svg|png)$/,
  /^\/sw\.js$/,
];

/** Yetkilendirme gerektirmeyen (herkese açık) path'ler. */
function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((re) => re.test(pathname));
}

// NOT: Giriş ekranı geçici olarak devre dışı bırakıldı. Tüm istekler
// doğrudan hedef sayfaya geçer; auth redirect zinciri askıya alındı.
// Geri açmak için aşağıdaki `AUTH_DISABLED` bayrağını `false` yap veya
// NEXT_PUBLIC_AUTH_MIDDLEWARE_ENABLED=true env değeriyle override et.
const AUTH_DISABLED = false;

export function middleware(req: NextRequest): NextResponse {
  if (AUTH_DISABLED || process.env.NEXT_PUBLIC_AUTH_MIDDLEWARE_ENABLED === "false") {
    return NextResponse.next();
  }

  const { pathname, search } = req.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const hasSession = req.cookies.get(SESSION_COOKIE)?.value;
  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = req.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  loginUrl.searchParams.set("next", pathname + (search || ""));
  return NextResponse.redirect(loginUrl);
}

/**
 * Yalnızca dashboard rotalarında çalış. `/login`, public policy sayfaları,
 * statik varlıklar, API rotaları ve Next internal dosyaları dışarıda.
 */
export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|assets|public|robots.txt|sitemap.xml|manifest.json|icon-|sw.js|login|reset-password|forgot-password|terms|privacy).*)",
  ],
};
