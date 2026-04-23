#!/usr/bin/env python3
"""Regenerate cover SVGs in clean AV DS 2026 style.
Flat geometry, no headline text, subtle FBRK marker only."""
import os

OUT = os.path.join(os.path.dirname(__file__), 'img')

# Per-article palette + minimal motif. Palette = dark deep color + muted tint.
# Motif = simple geometric shape placed at center.
COVERS = [
    ('001-grecia',    '#2d3142', '#6b7b8c', 'passport'),
    ('002-vena',      '#1a2e57', '#3d5a96', 'columns'),
    ('003-knb',       '#1f1a2e', '#4a3f6b', 'lock'),
    ('004-yaschur',   '#2a2418', '#8a6a3d', 'waves'),
    ('005-neftegaz',  '#1a1f2e', '#4a5a7a', 'derrick'),
    ('006-enpf',      '#0c1228', '#364872', 'bars'),
    ('007-police',    '#0f1a2e', '#3a5278', 'shield'),
    ('008-ktzh',      '#1e2418', '#5a6b3d', 'rails'),
    ('009-kanal',     '#0e2230', '#2d5a7a', 'water'),
    ('010-kokshetau', '#1f1e2e', '#3d3a6b', 'gavel'),
    ('011-abenov',    '#2e1f1f', '#7a4a3d', 'papers'),
    ('012-agro',      '#1e2618', '#4a6b3d', 'field'),
]

def grid_pattern(id_):
    return f'''<pattern id="{id_}" width="48" height="48" patternUnits="userSpaceOnUse">
      <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#fff" stroke-width="0.5" opacity="0.06"/>
    </pattern>'''

def motif_svg(kind):
    """Return inline SVG markup for a minimal centered motif."""
    # Center at (800, 450). Use white with low opacity.
    m = {
        'passport': '<rect x="700" y="340" width="200" height="260" rx="8" fill="none" stroke="#fff" stroke-width="3" opacity="0.55"/><circle cx="800" cy="460" r="38" fill="none" stroke="#fff" stroke-width="2.5" opacity="0.6"/><line x1="740" y1="530" x2="860" y2="530" stroke="#fff" stroke-width="2" opacity="0.5"/><line x1="740" y1="548" x2="860" y2="548" stroke="#fff" stroke-width="2" opacity="0.5"/>',
        'columns': '<g opacity="0.55" stroke="none" fill="#fff"><polygon points="660,350 940,350 920,330 680,330"/><rect x="685" y="355" width="28" height="210"/><rect x="731" y="355" width="28" height="210"/><rect x="777" y="355" width="28" height="210"/><rect x="823" y="355" width="28" height="210"/><rect x="869" y="355" width="28" height="210"/><rect x="660" y="568" width="280" height="14"/></g>',
        'lock': '<g opacity="0.6" fill="none" stroke="#fff" stroke-width="3"><rect x="720" y="430" width="160" height="130" rx="10"/><path d="M 750 430 L 750 390 Q 750 350 800 350 Q 850 350 850 390 L 850 430"/><circle cx="800" cy="490" r="10" fill="#fff"/></g>',
        'waves': '<g stroke="#fff" stroke-width="2.5" fill="none" opacity="0.5"><path d="M 200 450 Q 400 410 600 450 T 1000 450 T 1400 450"/><path d="M 200 490 Q 400 450 600 490 T 1000 490 T 1400 490"/><path d="M 200 530 Q 400 490 600 530 T 1000 530 T 1400 530"/></g>',
        'derrick': '<g opacity="0.55" stroke="#fff" stroke-width="2.5" fill="none"><polygon points="770,580 830,580 820,340 780,340"/><line x1="780" y1="380" x2="820" y2="380"/><line x1="780" y1="420" x2="820" y2="420"/><line x1="780" y1="460" x2="820" y2="460"/><line x1="780" y1="500" x2="820" y2="500"/><line x1="780" y1="540" x2="820" y2="540"/><line x1="800" y1="340" x2="800" y2="300"/><rect x="788" y="290" width="24" height="14" fill="#fff"/></g>',
        'bars': '<g opacity="0.55" fill="#fff"><rect x="640" y="520" width="36" height="70"/><rect x="700" y="480" width="36" height="110"/><rect x="760" y="440" width="36" height="150"/><rect x="820" y="410" width="36" height="180"/><rect x="880" y="460" width="36" height="130"/><rect x="940" y="495" width="36" height="95"/></g>',
        'shield': '<path d="M 800 340 L 900 380 L 900 480 Q 900 560 800 600 Q 700 560 700 480 L 700 380 Z" fill="none" stroke="#fff" stroke-width="3" opacity="0.6"/><path d="M 770 470 L 795 495 L 835 445" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.65"/>',
        'rails': '<g opacity="0.55" stroke="#fff" fill="#fff"><rect x="720" y="380" width="6" height="220"/><rect x="874" y="380" width="6" height="220"/><g stroke-width="0"><rect x="700" y="400" width="200" height="8"/><rect x="700" y="440" width="200" height="8"/><rect x="700" y="480" width="200" height="8"/><rect x="700" y="520" width="200" height="8"/><rect x="700" y="560" width="200" height="8"/></g></g>',
        'water': '<g opacity="0.55" fill="none" stroke="#fff" stroke-width="2.5"><path d="M 500 400 L 500 560 L 1100 560 L 1100 400"/><path d="M 500 480 L 1100 480"/><path d="M 650 480 L 650 560"/><path d="M 800 480 L 800 560"/><path d="M 950 480 L 950 560"/></g>',
        'gavel': '<g opacity="0.6" stroke="#fff" stroke-width="3" fill="none"><line x1="690" y1="390" x2="870" y2="560" stroke-linecap="round"/><rect x="640" y="340" width="140" height="60" rx="6" transform="rotate(40 710 370)"/><line x1="700" y1="600" x2="900" y2="600" stroke-width="4"/></g>',
        'papers': '<g opacity="0.55" stroke="#fff" stroke-width="2" fill="none"><rect x="700" y="370" width="180" height="230"/><rect x="720" y="350" width="180" height="230"/><line x1="740" y1="400" x2="880" y2="400"/><line x1="740" y1="430" x2="880" y2="430"/><line x1="740" y1="460" x2="840" y2="460"/><line x1="740" y1="490" x2="880" y2="490"/><line x1="740" y1="520" x2="860" y2="520"/></g>',
        'field': '<g opacity="0.55" stroke="#fff" stroke-width="1.5"><path d="M 300 560 L 1300 560 M 300 560 L 400 400 M 500 560 L 600 400 M 700 560 L 800 400 M 900 560 L 1000 400 M 1100 560 L 1200 400 M 400 400 L 1200 400"/></g>',
    }
    return m.get(kind, '')

def make_svg(slug, c1, c2, motif):
    gid = f'g_{slug}'
    pid = f'p_{slug}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}" stop-opacity="0.85"/>
    </linearGradient>
    {grid_pattern(pid)}
  </defs>
  <rect width="1600" height="900" fill="{c1}"/>
  <rect width="1600" height="900" fill="url(#{gid})"/>
  <rect width="1600" height="900" fill="url(#{pid})"/>
  {motif_svg(motif)}
  <g opacity="0.6">
    <rect x="80" y="800" width="4" height="40" fill="#fff"/>
    <text x="100" y="828" font-family="system-ui, sans-serif" font-size="18" font-weight="600" fill="#fff" letter-spacing="3">ФБРК</text>
  </g>
</svg>'''

for slug, c1, c2, motif in COVERS:
    path = os.path.join(OUT, f'{slug}.svg')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(make_svg(slug, c1, c2, motif))
    print('wrote', path)

print('done')
