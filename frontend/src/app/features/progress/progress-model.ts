import { LEVELS, Level, TopicStats, TopicSummary } from '../../core/models';

export interface TopicRow {
  id: string;
  title: string;
  level: Level;
  attempts: number;
  correct: number;
  /** From 0 to 1. It is 0 when there is no attempt. */
  accuracy: number;
}

export interface DayCell {
  /** ISO date, YYYY-MM-DD. */
  date: string;
  active: boolean;
}

export interface ErrorRow {
  ruleRef: string;
  topicId: string;
  slug: string;
  label: string;
  count: number;
}

/** One row for each topic, also for the topics without attempts. Sorted by level, then title. */
export function buildRows(topics: TopicSummary[], stats: TopicStats[]): TopicRow[] {
  const byTopic = new Map(stats.map((s) => [s.topic_id, s]));
  return topics
    .map((topic) => {
      const stat = byTopic.get(topic.id);
      const attempts = stat?.attempts ?? 0;
      const correct = stat?.correct ?? 0;
      return {
        id: topic.id,
        title: topic.title,
        level: topic.level,
        attempts,
        correct,
        accuracy: attempts ? correct / attempts : 0,
      };
    })
    .sort(
      (a, b) =>
        LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || a.title.localeCompare(b.title),
    );
}

/** The last `days` days, the oldest first. The last cell is `today` (UTC date). */
export function buildStrip(activeDays: string[], today: Date, days = 30): DayCell[] {
  const active = new Set(activeDays);
  return Array.from({ length: days }, (_, i) => {
    const day = new Date(today.getTime() - (days - 1 - i) * 86_400_000);
    const date = day.toISOString().slice(0, 10);
    return { date, active: active.has(date) };
  });
}

/** The rules with most errors first. The label uses the topic title when it is known. */
export function buildErrors(
  errors: Record<string, number>,
  topics: TopicSummary[],
): ErrorRow[] {
  return Object.entries(errors)
    .map(([ruleRef, count]) => {
      const [topicId, slug = ''] = ruleRef.split('#');
      const title = topics.find((t) => t.id === topicId)?.title ?? topicId;
      return { ruleRef, topicId, slug, label: `${title} · ${slug}`, count };
    })
    .sort((a, b) => b.count - a.count || a.ruleRef.localeCompare(b.ruleRef));
}
