// Run: node src/lib/labels.check.mjs
import assert from "node:assert/strict";
import { deadlineLabel, describeStatute } from "./labels.ts";

assert.deepEqual(describeStatute("35 USC 103"), { kind: "진보성 없음", law: "미국 특허법 제103조" });
assert.deepEqual(describeStatute("35 USC 112(b)"), { kind: "기재 불명확", law: "미국 특허법 제112조 b항" });
assert.deepEqual(describeStatute("35 USC 102(a)(1)"), { kind: "신규성 없음", law: "미국 특허법 제102조 a항 1호" });
assert.equal(describeStatute("35 USC 112(f)").kind, "기재 요건 위반");
assert.equal(describeStatute("35 USC 112(b)", true).kind, "형식 지적");
assert.deepEqual(describeStatute("특허법 제29조제2항"), { kind: "진보성 없음", law: "특허법 제29조제2항" });
assert.equal(describeStatute("특허법 제42조제4항제2호").kind, "청구범위 기재 요건 위반");
assert.equal(describeStatute("특허법 제42조의2").kind, "기재 요건 위반");
assert.deepEqual(describeStatute("unknown"), { kind: "거절 이유", law: "법조항 확인 필요" });

const today = new Date(2026, 9, 13);
assert.deepEqual(deadlineLabel("2026-11-20", today), { text: "38일 남음", soon: false });
assert.deepEqual(deadlineLabel("2026-10-24", today), { text: "11일 남음", soon: true });
assert.deepEqual(deadlineLabel("2026-10-13", today), { text: "오늘 마감", soon: true });
assert.deepEqual(deadlineLabel("2026-10-10", today), { text: "3일 지남", soon: true });
assert.deepEqual(deadlineLabel(null, today), { text: "기한 없음", soon: false });
console.log("labels ok");
