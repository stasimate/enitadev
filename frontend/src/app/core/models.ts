/** Types that mirror the backend Pydantic models (backend/enita/models.py). */

export type Level = 'A1' | 'A2' | 'B1';

export const LEVELS: readonly Level[] = ['A1', 'A2', 'B1'];

export interface TopicSummary {
  id: string;
  title: string;
  level: Level;
  tags: string[];
}

export interface Section {
  slug: string;
  title: string;
  markdown: string;
}

export interface TopicCard extends TopicSummary {
  sections: Section[];
}
