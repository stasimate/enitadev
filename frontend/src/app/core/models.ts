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

export type ExerciseType =
  'fill_blank' | 'multiple_choice' | 'reorder' | 'transform' | 'find_error';

export interface Exercise {
  id: string;
  topic_id: string;
  type: ExerciseType;
  instruction: string;
  /**
   * Depends on the type. fill_blank: English sentence with `___` for the answer.
   * transform: English source sentence. find_error: English sentence with one wrong word.
   * reorder: Italian translation of the target sentence (a hint).
   */
  prompt: string;
  /**
   * multiple_choice: the choices. reorder: shuffled English chunks.
   * find_error: the words of the sentence in order. Empty for the other types.
   */
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
