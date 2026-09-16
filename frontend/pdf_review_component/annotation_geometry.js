'use strict';

// Display geometry only. Never change the source boxes or Evidence offsets.
window.PatentAnnotationGeometry = (() => {
  const valid = box => Array.isArray(box) && box.length === 4 && box.every(Number.isFinite) &&
    box[0] < box[2] && box[1] < box[3];
  const unique = boxes => [...new Map(boxes.filter(valid).map(box => [box.join(','), box])).values()];

  function claimRegions(boxes, pageBoxes = boxes) {
    const source = unique(boxes);
    // Horizontal projection of the page's Claim lines identifies column bands.
    // Join overlapping spans only; never bridge even a narrow column gutter.
    const bands = [];
    for (const box of unique([...pageBoxes, ...source]).sort((a, b) => a[0] - b[0])) {
      const band = bands[bands.length - 1];
      if (band && box[0] <= band[1]) band[1] = Math.max(band[1], box[2]);
      else bands.push([box[0], box[2]]);
    }
    return bands.flatMap(([left, right]) => {
      const column = source.filter(box => box[0] >= left && box[2] <= right);
      if (!column.length) return [];
      // Bounds come only from THIS Claim, not other Claims in the column.
      return [[
        Math.min(...column.map(box => box[0])), Math.min(...column.map(box => box[1])),
        Math.max(...column.map(box => box[2])), Math.max(...column.map(box => box[3])),
      ]];
    });
  }

  function groupAnnotations(annotations) {
    const groups = new Map();
    for (const annotation of annotations) {
      const key = JSON.stringify([
        annotation.document_id, annotation.page,
        annotation.claim_number == null ? annotation.item_id : 'claim-' + annotation.claim_number,
      ]);
      if (!groups.has(key)) groups.set(key, {...annotation, boxes: []});
      groups.get(key).boxes.push(...annotation.boxes);
    }
    return [...groups.values()].map(group => ({...group, boxes: unique(group.boxes)}));
  }

  return Object.freeze({claimRegions, groupAnnotations});
})();
