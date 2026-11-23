import { TopicSummary } from '../../core/models';
import { buildErrors, buildRows, buildStrip } from './progress-model';

const TOPICS: TopicSummary[] = [
  { id: 'b1', title: 'Zeta', level: 'B1', tags: [] },
  { id: 'a2', title: 'Beta', level: 'A2', tags: [] },
  { id: 'a1', title: 'Alfa', level: 'A1', tags: [] },
];

describe('buildRows', () => {
  it('lists all topics sorted by level, with 0 for topics without attempts', () => {
    const rows = buildRows(TOPICS, [{ topic_id: 'a2', attempts: 4, correct: 3, accuracy: 0.75 }]);
    expect(rows.map((r) => r.id)).toEqual(['a1', 'a2', 'b1']);
    expect(rows[0]).toMatchObject({ attempts: 0, correct: 0, accuracy: 0 });
    expect(rows[1]).toMatchObject({ attempts: 4, correct: 3, accuracy: 0.75 });
  });
});

describe('buildStrip', () => {
  it('makes 30 cells that end today and marks the active days', () => {
    const strip = buildStrip(['2026-11-23', '2026-11-01', '2020-01-01'], new Date('2026-11-23T10:00:00Z'));
    expect(strip.length).toBe(30);
    expect(strip[29]).toEqual({ date: '2026-11-23', active: true });
    expect(strip[0].date).toBe('2026-10-25');
    expect(strip.filter((c) => c.active).map((c) => c.date)).toEqual(['2026-11-01', '2026-11-23']);
  });
});

describe('buildErrors', () => {
  it('sorts by count and labels with the topic title', () => {
    const rows = buildErrors({ 'a1#uno': 1, 'a2#due': 5 }, TOPICS);
    expect(rows.map((r) => r.ruleRef)).toEqual(['a2#due', 'a1#uno']);
    expect(rows[0]).toMatchObject({ topicId: 'a2', slug: 'due', label: 'Beta · due' });
  });
});
