"use client";

import { useCase } from "../case-shell";

// Phase 3: port frontend/relationship_map_component/map.js as a React SVG component.
export default function MapPage() {
  const { relationship } = useCase().detail;
  return (
    <p className="muted">
      관계 지도는 다음 단계에서 이식합니다. 노드 {relationship.nodes.length}개 · 연결 {relationship.edges.length}개
    </p>
  );
}
