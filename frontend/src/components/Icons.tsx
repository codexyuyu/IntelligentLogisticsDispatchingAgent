
type IconProps = { size?: number };

const paths: Record<string, string[]> = {
  bot: ['M12 3v3','M6 7h12a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-7a3 3 0 0 1 3-3z','M8 12h.01','M16 12h.01','M9 16h6'],
  grid: ['M4 4h6v6H4z', 'M14 4h6v6h-6z', 'M4 14h6v6H4z', 'M14 14h6v6h-6z'],
  package: ['M4 7.5 12 3l8 4.5', 'M4 7.5V17l8 4.5 8-4.5V7.5', 'M12 12v9.5', 'M8 5l8 4.5'],
  warehouse: ['M3 10 12 4l9 6', 'M5 9v10h14V9', 'M8 19v-6h8v6', 'M7 10h10'],
  truck: ['M3 6h11v10H3z', 'M14 10h4l3 3v3h-7z', 'M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4', 'M18 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4'],
  route: ['M5 19c5 0 5-14 10-14 2 0 4 1 4 4', 'M18 5h3v3', 'M5 5h.01', 'M19 19h.01'],
  alert: ['M12 3 2 20h20L12 3z', 'M12 9v4', 'M12 17h.01'],
  play: ['M7 4v16l13-8z'],
  chart: ['M4 19V5', 'M4 19h16', 'M7 16v-5', 'M11 16V8', 'M15 16v-9', 'M19 16v-3'],
  list: ['M5 6h14', 'M5 12h14', 'M5 18h14'],
  clock: ['M12 6v6l4 2', 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18'],
  check: ['m5 12 4 4L19 6'],
  plus: ['M12 5v14', 'M5 12h14'],
  refresh: ['M20 12a8 8 0 0 0-13.7-5.7L4 8', 'M4 4v4h4', 'M4 12a8 8 0 0 0 13.7 5.7L20 16', 'M20 20v-4h-4'],
  search: ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16', 'm21 21-4.3-4.3'],
  database: ['M4 6c0-2 4-3 8-3s8 1 8 3-4 3-8 3-8-1-8-3z', 'M4 6v6c0 2 4 3 8 3s8-1 8-3V6', 'M4 12v6c0 2 4 3 8 3s8-1 8-3v-6'],
  file: ['M6 3h8l4 4v14H6z', 'M14 3v5h5', 'M9 13h6', 'M9 17h6'],
  chevron: ['m9 6 6 6-6 6'],
};

export default function Icon({ name, size = 18 }: { name: keyof typeof paths; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name].map((d) => <path key={d} d={d} />)}
    </svg>
  );
}
