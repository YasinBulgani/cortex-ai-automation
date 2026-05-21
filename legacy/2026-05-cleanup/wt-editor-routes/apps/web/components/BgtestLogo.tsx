import type React from "react";

export function BgtestLogo({ className = "h-10", ...rest }: React.SVGProps<SVGSVGElement> & { className?: string }) {
  return (
    <svg
      viewBox="0 0 280 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Visium Operations"
      {...rest}
    >
      {/* Shield icon */}
      <path
        d="M6 4C6 4 14 7 22 7C30 7 38 4 38 4C38 4 39.5 22 38 31C36.5 40 22 50 22 50C22 50 8 40 6.5 31C5 22 6 4 6 4Z"
        stroke="#1B8C4E"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Checkmark inside shield */}
      <path
        d="M14 27L20 33L30 22"
        stroke="#1B8C4E"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <text x="50" y="36" fontFamily="system-ui, -apple-system, sans-serif" fontWeight="800" fontSize="30" letterSpacing="0.8" fill="#F8FAFC">
        VISIU
      </text>
      <text x="146" y="36" fontFamily="system-ui, -apple-system, sans-serif" fontWeight="800" fontSize="30" letterSpacing="0.8" fill="#1B8C4E">
        M
      </text>
      <text x="50" y="52" fontFamily="system-ui, -apple-system, sans-serif" fontWeight="700" fontSize="11" letterSpacing="2.6" fill="#94A3B8">
        OPERATIONS
      </text>
    </svg>
  );
}
