// Same mark as the AutoPIL dashboard (packages/dashboard/src/components/ui/LogoMark.tsx).
export function LogoMark({ width = 32, height = 36, id = "logo" }: { width?: number; height?: number; id?: string }) {
  return (
    <svg width={width} height={height} viewBox="0 0 46 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id={`${id}-face`} cx="38%" cy="28%" r="68%">
          <stop offset="0%" stopColor="rgba(0,220,240,0.30)" />
          <stop offset="55%" stopColor="rgba(0,204,221,0.10)" />
          <stop offset="100%" stopColor="rgba(0,60,80,0.15)" />
        </radialGradient>
        <filter id={`${id}-glow`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="1.4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <path d="M24 4L42 12.5V26C42 38 33 46 24 50C15 46 6 38 6 26V12.5L24 4Z" fill="rgba(0,45,65,0.65)" />
      <path d="M22 2L40 10.5V24C40 36 31 44 22 48C13 44 4 36 4 24V10.5L22 2Z" fill={`url(#${id}-face)`} stroke="#00ccdd" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M22 2.5L39.5 10.8V17.5C33.5 14.5 27.5 13 22 12.5C16.5 13 10.5 14.5 4.5 17.5V10.8L22 2.5Z" fill="rgba(120,240,252,0.14)" />
      <path d="M22 2L4 10.5V24C4 35.5 12.5 43.5 22 47.5" stroke="rgba(180,245,255,0.22)" strokeWidth="1.2" strokeLinejoin="round" strokeLinecap="round" />
      <line x1="13" y1="18" x2="31" y2="18" stroke="#00ccdd" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="16.5" y1="25.5" x2="27.5" y2="25.5" stroke="#00ccdd" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="22" cy="35" r="2.8" fill="#00ccdd" filter={`url(#${id}-glow)`} />
      <circle cx="21.2" cy="34.2" r="0.9" fill="rgba(210,255,255,0.85)" />
    </svg>
  );
}
