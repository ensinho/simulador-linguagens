import { useMemo } from 'react';

export interface GraphEdge {
  de: string;
  para: string;
  label: string;
  key: string;
}

interface StateGraphProps {
  states: string[];
  initialState: string;
  acceptStates: string[];
  rejectStates?: string[];
  edges: GraphEdge[];
  activeStates: string[];
  activeEdgeKeys: string[];
  finalVerdict?: 'accept' | 'reject' | null;
}

interface NodePos {
  x: number;
  y: number;
  rx: number;
  ry: number;
}

function nodeSize(label: string): { rx: number; ry: number } {
  const len = label.length;
  if (len <= 3) return { rx: 24, ry: 24 };
  if (len <= 5) return { rx: 28, ry: 24 };
  const rx = Math.min(72, Math.max(36, len * 4.4 + 14));
  return { rx, ry: 22 };
}

function buildLayout(
  states: string[],
  initialState: string,
  edges: GraphEdge[],
  rejectStates: string[]
): { positions: Record<string, NodePos>; width: number; height: number } {
  const rejectSet = new Set(rejectStates);
  const separateReject = states.length > 5 && rejectStates.length > 0;
  const mainStates = separateReject
    ? states.filter((s) => !rejectSet.has(s))
    : states;

  const adj = new Map<string, string[]>();
  for (const s of mainStates) adj.set(s, []);
  for (const e of edges) {
    if (e.de === e.para) continue;
    if (separateReject && (rejectSet.has(e.de) || rejectSet.has(e.para))) continue;
    const list = adj.get(e.de);
    if (list && !list.includes(e.para)) list.push(e.para);
  }

  const layerOf = new Map<string, number>();
  const queue: string[] = [];
  if (mainStates.includes(initialState)) {
    layerOf.set(initialState, 0);
    queue.push(initialState);
  }
  while (queue.length > 0) {
    const u = queue.shift()!;
    const d = layerOf.get(u)!;
    for (const v of adj.get(u) ?? []) {
      if (!layerOf.has(v)) {
        layerOf.set(v, d + 1);
        queue.push(v);
      }
    }
  }

  let maxLayer = 0;
  for (const d of layerOf.values()) maxLayer = Math.max(maxLayer, d);
  for (const s of mainStates) {
    if (!layerOf.has(s)) {
      maxLayer += 1;
      layerOf.set(s, maxLayer);
    }
  }

  const cols: string[][] = Array.from({ length: maxLayer + 1 }, () => []);
  for (const s of mainStates) cols[layerOf.get(s)!].push(s);

  const maxColLen = Math.max(1, ...cols.map((c) => c.length));
  const maxRx = Math.max(...states.map((s) => nodeSize(s).rx));
  const colGap = Math.max(155, maxRx * 2 + 86);
  const rowGap = 98;
  const padX = Math.max(76, maxRx + 46);
  const padTop = 70;
  const padBottom = separateReject ? 120 : 58;

  const contentH = Math.max(110, (maxColLen - 1) * rowGap);
  const positions: Record<string, NodePos> = {};

  cols.forEach((col, ci) => {
    const x = padX + ci * colGap;
    const colH = (col.length - 1) * rowGap;
    const startY = padTop + (contentH - colH) / 2;
    col.forEach((s, ri) => {
      const { rx, ry } = nodeSize(s);
      positions[s] = { x, y: startY + ri * rowGap, rx, ry };
    });
  });

  const width = Math.max(500, padX * 2 + Math.max(0, cols.length - 1) * colGap);
  let height = padTop + contentH + padBottom;

  if (separateReject) {
    const rejY = padTop + contentH + 68;
    rejectStates.forEach((s, idx) => {
      const { rx, ry } = nodeSize(s);
      const x = width / 2 + (idx - (rejectStates.length - 1) / 2) * 140;
      positions[s] = { x, y: rejY, rx, ry };
    });
    height = rejY + 48;
  }

  return { positions, width, height };
}

function edgeEndpoint(from: NodePos, tx: number, ty: number, pad = 0) {
  const dx = tx - from.x;
  const dy = ty - from.y;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const rx = from.rx + pad;
  const ry = from.ry + pad;
  const scale = 1 / Math.hypot(ux / rx, uy / ry);
  return { x: from.x + ux * scale, y: from.y + uy * scale };
}

export function StateGraph({
  states,
  initialState,
  acceptStates,
  rejectStates = [],
  edges,
  activeStates,
  activeEdgeKeys,
  finalVerdict = null,
}: StateGraphProps) {
  const activeSet = useMemo(() => new Set(activeStates), [activeStates]);
  const acceptSet = useMemo(() => new Set(acceptStates), [acceptStates]);
  const rejectSet = useMemo(() => new Set(rejectStates), [rejectStates]);
  const activeEdgeSet = useMemo(() => new Set(activeEdgeKeys), [activeEdgeKeys]);

  const { positions, width, height } = useMemo(
    () => buildLayout(states, initialState, edges, rejectStates),
    [states, initialState, edges, rejectStates]
  );

  const grouped = useMemo(() => {
    const map = new Map<
      string,
      { de: string; para: string; labels: string[]; active: boolean }
    >();
    for (const e of edges) {
      const k = `${e.de}__${e.para}`;
      const hit = activeEdgeSet.has(e.key);
      const cur = map.get(k);
      if (cur) {
        if (!cur.labels.includes(e.label)) cur.labels.push(e.label);
        if (hit) cur.active = true;
      } else {
        map.set(k, { de: e.de, para: e.para, labels: [e.label], active: hit });
      }
    }
    return Array.from(map.values());
  }, [edges, activeEdgeSet]);

  const pairSet = useMemo(() => {
    const s = new Set<string>();
    for (const g of grouped) s.add(`${g.de}__${g.para}`);
    return s;
  }, [grouped]);

  const initPos = positions[initialState];

  return (
    <div className="graph-box">
      <svg
        className="graph-svg"
        viewBox={`0 0 ${width} ${height}`}
        style={{ maxHeight: states.length > 5 ? 380 : 270 }}
        role="img"
        aria-label="Diagrama de estados"
      >
        <defs>
          <marker
            id="arr-ink"
            viewBox="0 0 10 10"
            refX="8.5"
            refY="5"
            markerWidth="6.5"
            markerHeight="6.5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.2 L 9 5 L 0 8.8 z" fill="#334155" />
          </marker>
          <marker
            id="arr-muted"
            viewBox="0 0 10 10"
            refX="8.5"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.2 L 9 5 L 0 8.8 z" fill="#94a3b8" />
          </marker>
          <marker
            id="arr-blue"
            viewBox="0 0 10 10"
            refX="8.5"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.2 L 9 5 L 0 8.8 z" fill="#1d4ed8" />
          </marker>
          <marker
            id="arr-red"
            viewBox="0 0 10 10"
            refX="8.5"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.2 L 9 5 L 0 8.8 z" fill="#b91c1c" />
          </marker>
        </defs>

        {initPos && (
          <g>
            <line
              x1={Math.max(8, initPos.x - initPos.rx - 34)}
              y1={initPos.y}
              x2={initPos.x - initPos.rx - 4}
              y2={initPos.y}
              stroke="#0f172a"
              strokeWidth="2.2"
              markerEnd="url(#arr-ink)"
            />
            <text
              x={Math.max(10, initPos.x - initPos.rx - 32)}
              y={initPos.y - 9}
              fontSize="10.5"
              fontWeight="700"
              fill="#334155"
              fontFamily="var(--font-sans)"
            >
              início
            </text>
          </g>
        )}

        {[...grouped]
          .sort((a, b) => Number(a.active) - Number(b.active))
          .map((g) => {
            const p1 = positions[g.de];
            const p2 = positions[g.para];
            if (!p1 || !p2) return null;

            const toReject = rejectSet.has(g.para) && states.length > 5;
            const stroke = g.active
              ? toReject
                ? '#b91c1c'
                : '#1d4ed8'
              : toReject
                ? '#94a3b8'
                : '#475569';
            const strokeWidth = g.active ? 3 : 1.7;
            const marker = g.active
              ? toReject
                ? 'url(#arr-red)'
                : 'url(#arr-blue)'
              : toReject
                ? 'url(#arr-muted)'
                : 'url(#arr-ink)';

            const text = g.labels.join(', ');
            const label =
              text.length > 24 ? `${g.labels.slice(0, 2).join(', ')}…` : text;

            if (g.de === g.para) {
              const topY = p1.y - p1.ry;
              const d = `M ${p1.x - 14} ${topY + 2} C ${p1.x - 30} ${
                topY - 40
              }, ${p1.x + 30} ${topY - 40}, ${p1.x + 14} ${topY - 2}`;
              return (
                <g key={`${g.de}__${g.para}`}>
                  <path
                    d={d}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                    markerEnd={marker}
                  />
                  <text
                    x={p1.x}
                    y={topY - 36}
                    textAnchor="middle"
                    fontSize="12"
                    fontWeight="700"
                    fontFamily="var(--font-mono)"
                    fill={g.active ? '#1d4ed8' : '#0f172a'}
                    stroke="#ffffff"
                    strokeWidth="4"
                    paintOrder="stroke"
                  >
                    {label}
                  </text>
                </g>
              );
            }

            const hasReverse = pairSet.has(`${g.para}__${g.de}`);
            const isBack = p2.x < p1.x - 10;
            const dx = p2.x - p1.x;
            const dy = p2.y - p1.y;
            const dist = Math.hypot(dx, dy) || 1;
            const nx = -dy / dist;
            const ny = dx / dist;

            let offset = 0;
            if (hasReverse) offset = 26;
            else if (isBack && Math.abs(dy) < 35) offset = 50;
            else if (toReject) offset = 14;

            const mx = (p1.x + p2.x) / 2 + nx * offset;
            const my = (p1.y + p2.y) / 2 + ny * offset;

            const start = edgeEndpoint(p1, mx, my, 1);
            const end = edgeEndpoint(p2, mx, my, 4);
            const pathD =
              offset === 0
                ? `M ${start.x} ${start.y} L ${end.x} ${end.y}`
                : `M ${start.x} ${start.y} Q ${mx} ${my} ${end.x} ${end.y}`;

            const lx = 0.25 * start.x + 0.5 * mx + 0.25 * end.x;
            const ly =
              0.25 * start.y + 0.5 * my + 0.25 * end.y + (offset === 0 ? -9 : 0);

            return (
              <g key={`${g.de}__${g.para}`}>
                <path
                  d={pathD}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  strokeDasharray={toReject && !g.active ? '4 4' : undefined}
                  markerEnd={marker}
                />
                {(!toReject || g.active) && (
                  <text
                    x={lx}
                    y={ly}
                    textAnchor="middle"
                    fontSize="12"
                    fontWeight="700"
                    fontFamily="var(--font-mono)"
                    fill={
                      g.active ? (toReject ? '#b91c1c' : '#1d4ed8') : '#0f172a'
                    }
                    stroke="#ffffff"
                    strokeWidth="4.5"
                    paintOrder="stroke"
                  >
                    {label}
                  </text>
                )}
              </g>
            );
          })}

        {states.map((s) => {
          const pos = positions[s];
          if (!pos) return null;
          const active = activeSet.has(s);
          const accept = acceptSet.has(s);
          const reject = rejectSet.has(s);

          let fill = '#ffffff';
          let stroke = '#1e293b';
          let innerStroke = '#15803d';
          let textColor = '#0f172a';
          let strokeWidth = 2;

          if (active) {
            strokeWidth = 2.5;
            if (finalVerdict === 'accept' && accept) {
              fill = '#15803d';
              stroke = '#14532d';
              innerStroke = '#bbf7d0';
              textColor = '#ffffff';
            } else if ((finalVerdict === 'reject' && !accept) || reject) {
              fill = '#b91c1c';
              stroke = '#7f1d1d';
              innerStroke = '#fecaca';
              textColor = '#ffffff';
            } else {
              fill = '#1d4ed8';
              stroke = '#1e3a8a';
              innerStroke = '#bfdbfe';
              textColor = '#ffffff';
            }
          } else if (accept) {
            stroke = '#15803d';
            innerStroke = '#15803d';
          } else if (reject) {
            stroke = '#b91c1c';
            fill = '#fef2f2';
            textColor = '#991b1b';
          }

          const r = pos.rx === pos.ry ? pos.rx : pos.ry;

          return (
            <g key={s}>
              <rect
                x={pos.x - pos.rx}
                y={pos.y - pos.ry}
                width={pos.rx * 2}
                height={pos.ry * 2}
                rx={r}
                fill={fill}
                stroke={stroke}
                strokeWidth={strokeWidth}
              />
              {accept && (
                <rect
                  x={pos.x - pos.rx + 4.5}
                  y={pos.y - pos.ry + 4.5}
                  width={(pos.rx - 4.5) * 2}
                  height={(pos.ry - 4.5) * 2}
                  rx={Math.max(4, r - 4.5)}
                  fill="none"
                  stroke={innerStroke}
                  strokeWidth="1.6"
                />
              )}
              <text
                x={pos.x}
                y={pos.y + 4.5}
                textAnchor="middle"
                fontSize={s.length > 10 ? '11' : '13'}
                fontWeight="700"
                fontFamily="var(--font-mono)"
                fill={textColor}
              >
                {s}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
