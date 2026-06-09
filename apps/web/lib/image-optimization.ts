/**
 * Image Optimization Utilities
 *
 * - WebP format detection & fallback
 * - Responsive image generation
 * - Lazy loading configuration
 * - Image compression hints
 */

export interface ImageSet {
  src: string;
  srcset: string;
  sizes: string;
  alt: string;
  placeholder?: string;
  webpSrc?: string;
  webpSrcset?: string;
}

export interface ResponsiveImageOptions {
  maxWidth?: number;
  formats?: ("webp" | "png" | "jpg")[];
  quality?: number;
}

// ────────────────────────────────────────────────────────────
// Image Format Detection
// ────────────────────────────────────────────────────────────

let supportsWebP: boolean | null = null;

/**
 * Detect WebP support
 */
export async function checkWebPSupport(): Promise<boolean> {
  if (supportsWebP !== null) {
    return supportsWebP;
  }

  if (typeof window === "undefined") {
    return false;
  }

  return new Promise((resolve) => {
    const webP = new Image();
    webP.onload = webP.onerror = () => {
      supportsWebP = webP.height === 2;
      resolve(supportsWebP);
    };
    webP.src =
      "data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAAAwAQCdASoBAAEAAUAcJaACdLoB/gAA/v7+AAA=";
  });
}

/**
 * Get preferred image format
 */
export async function getPreferredImageFormat(): Promise<"webp" | "png" | "jpg"> {
  const supportsWebp = await checkWebPSupport();
  return supportsWebp ? "webp" : "png";
}

// ────────────────────────────────────────────────────────────
// Responsive Image URLs
// ────────────────────────────────────────────────────────────

/**
 * Generate Next.js Image Optimization URL
 */
export function getOptimizedImageUrl(
  src: string,
  width: number,
  format: "webp" | "png" | "jpg" = "webp"
): string {
  // Remove trailing slash if present
  const cleanSrc = src.replace(/\/$/, "");

  // For Next.js Image component, use /_next/image
  // For URL-based optimization, format is: /_next/image?url=&w=&q=&f=
  const params = new URLSearchParams({
    url: cleanSrc,
    w: width.toString(),
    q: "75", // quality
    f: format,
  });

  return `/_next/image?${params.toString()}`;
}

/**
 * Generate responsive srcset
 */
export function generateResponsiveSrcset(
  src: string,
  widths: number[] = [320, 640, 960, 1280, 1920],
  format: "webp" | "png" | "jpg" = "webp"
): string {
  return widths
    .map((width) => {
      const url = getOptimizedImageUrl(src, width, format);
      return `${url} ${width}w`;
    })
    .join(", ");
}

/**
 * Generate sizes attribute for responsive images
 */
export function generateSizes(breakpoints?: Record<string, string>): string {
  const defaults: Record<string, string> = {
    "100vw": "(max-width: 640px)",
    "80vw": "(max-width: 1024px)",
    "60vw": "(min-width: 1025px)",
  };

  const merged = { ...defaults, ...(breakpoints || {}) };

  return Object.entries(merged)
    .map(([size, media]) => `${media} ${size}`)
    .join(", ");
}

/**
 * Create picture element with WebP support
 */
export function createPictureElement(
  src: string,
  alt: string,
  options: ResponsiveImageOptions = {}
): string {
  const { maxWidth = 1920, formats = ["webp", "png"] } = options;

  const widths = [320, 640, 960, 1280, 1920].filter((w) => w <= maxWidth);
  const sizes = generateSizes();

  let html = "<picture>";

  // WebP source
  if (formats.includes("webp")) {
    const webpSrcset = generateResponsiveSrcset(src, widths, "webp");
    html += `<source srcset="${webpSrcset}" type="image/webp">`;
  }

  // PNG fallback
  if (formats.includes("png")) {
    const pngSrcset = generateResponsiveSrcset(src, widths, "png");
    html += `<source srcset="${pngSrcset}" type="image/png">`;
  }

  // Fallback img
  const fallback = getOptimizedImageUrl(src, Math.min(1280, maxWidth), "png");
  html += `<img src="${fallback}" alt="${alt.replace(/"/g, "&quot;")}" sizes="${sizes}" loading="lazy">`;

  html += "</picture>";

  return html;
}

// ────────────────────────────────────────────────────────────
// Lazy Loading Configuration
// ────────────────────────────────────────────────────────────

export interface LazyImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  priority?: boolean;
  className?: string;
  onLoad?: () => void;
  onError?: () => void;
  blur?: boolean;
}

/**
 * Generate blur placeholder (LQIP - Low Quality Image Placeholder)
 */
export function generateBlurDataUrl(
  color: string = "#e5e7eb",
  width: number = 10,
  height: number = 10
): string {
  const canvas = typeof window !== "undefined" ? document.createElement("canvas") : null;
  if (!canvas) return "";

  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";

  ctx.fillStyle = color;
  ctx.fillRect(0, 0, width, height);

  return canvas.toDataURL("image/png");
}

/**
 * Intersection Observer for lazy loading images
 */
export function lazyLoadImages(selector: string = "img[data-lazy]"): () => void {
  if (typeof window === "undefined") return () => {};

  if (!("IntersectionObserver" in window)) {
    // Fallback: load all images immediately
    document.querySelectorAll(selector).forEach((img: Element) => {
      const htmlImg = img as HTMLImageElement;
      if (htmlImg.dataset.lazy) {
        htmlImg.src = htmlImg.dataset.lazy;
        htmlImg.removeAttribute("data-lazy");
      }
    });
    return () => {};
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target as HTMLImageElement;
          if (img.dataset.lazy) {
            img.src = img.dataset.lazy;
            img.removeAttribute("data-lazy");
            observer.unobserve(img);
          }
        }
      });
    },
    {
      rootMargin: "50px 0px",
      threshold: 0.01,
    }
  );

  document.querySelectorAll(selector).forEach((img) => {
    observer.observe(img);
  });

  return () => {
    observer.disconnect();
  };
}

// ────────────────────────────────────────────────────────────
// Image Compression Hints
// ────────────────────────────────────────────────────────────

/**
 * Analyze image and recommend compression
 */
export async function analyzeImage(
  file: File
): Promise<{
  originalSize: number;
  estimatedCompressed: number;
  format: string;
  recommendations: string[];
}> {
  const recommendations: string[] = [];

  // Size recommendations
  if (file.size > 500 * 1024) {
    recommendations.push("Image is large (>500KB), consider compressing");
  }

  // Format recommendations
  if (file.type === "image/png" && file.size > 100 * 1024) {
    recommendations.push("PNG is large, consider WebP or JPEG");
  }

  // Estimate compression ratio
  const estimatedCompressed = Math.round(file.size * 0.6); // Assume ~40% reduction

  return {
    originalSize: file.size,
    estimatedCompressed,
    format: file.type.split("/")[1] || "unknown",
    recommendations,
  };
}

// ────────────────────────────────────────────────────────────
// Image Preloading
// ────────────────────────────────────────────────────────────

const preloadedImages = new Set<string>();

/**
 * Preload image
 */
export function preloadImage(src: string): Promise<HTMLImageElement> {
  if (preloadedImages.has(src)) {
    return Promise.resolve(new Image());
  }

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      preloadedImages.add(src);
      resolve(img);
    };
    img.onerror = reject;
    img.src = src;
  });
}

/**
 * Preload multiple images
 */
export async function preloadImages(srcs: string[]): Promise<HTMLImageElement[]> {
  return Promise.all(srcs.map((src) => preloadImage(src)));
}

// ────────────────────────────────────────────────────────────
// Critical Image Loading
// ────────────────────────────────────────────────────────────

/**
 * Add link preload for critical images
 */
export function addImagePreload(src: string, imagesrcset?: string): void {
  if (typeof document === "undefined") return;

  const link = document.createElement("link");
  link.rel = "preload";
  link.as = "image";
  link.href = src;

  if (imagesrcset) {
    link.setAttribute("imagesrcset", imagesrcset);
  }

  document.head.appendChild(link);
}

/**
 * Prefetch image resources
 */
export function prefetchImages(srcs: string[]): void {
  if (typeof document === "undefined") return;

  srcs.forEach((src) => {
    const link = document.createElement("link");
    link.rel = "prefetch";
    link.href = src;
    document.head.appendChild(link);
  });
}
