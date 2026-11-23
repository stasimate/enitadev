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

export type ExerciseType = 'fill_blank' | 'multiple_choice';

export interface Exercise {
  id: string;
  topic_id: string;
  type: ExerciseType;
  instruction: string;
  /** English sentence. A fill_blank prompt contains `___` where the answer goes. */
  prompt: string;
  /** Three or four choices for multiple_choice. Empty for fill_blank. */
  options: string[];
}

export type Verdict = 'correct' | 'partial' | 'wrong';

export interface Feedback {
  verdict: Verdict;
  score: number;
  correct_answer: string;
  explanation: string;
  /** Format: `<topic_id>#<section-slug>`. */
  rule_ref: string;
}
