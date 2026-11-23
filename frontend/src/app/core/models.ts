/** Types that mirror the backend Pydantic models (backend/enita/models.py). */

export type Level = 'A1' | 'A2' | 'B1' | 'B2';

export const LEVELS: readonly Level[] = ['A1', 'A2', 'B1', 'B2'];

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
  | 'fill_blank'
  | 'multiple_choice'
  | 'reorder'
  | 'transform'
  | 'find_error'
  | 'translate'
  | 'guided'
  | 'rewrite'
  | 'dialogue';

/** The types where the student writes free text. */
export const WRITING_TYPES: readonly ExerciseType[] = ['translate', 'guided', 'rewrite', 'dialogue'];

/** The maximum length of a free text answer. */
export const WRITING_MAX_LENGTH = 600;

export function isWriting(type: ExerciseType): boolean {
  return WRITING_TYPES.includes(type);
}

export interface Exercise {
  id: string;
  topic_id: string;
  type: ExerciseType;
  instruction: string;
  /**
   * Depends on the type. fill_blank: English sentence with `___` for the answer.
   * transform: English source sentence. find_error: English sentence with one wrong word.
   * reorder: Italian translation of the target sentence (a hint).
   * translate: Italian text to translate. guided: a writing task in Italian.
   * rewrite: an English text to rewrite. dialogue: a line of a character.
   */
  prompt: string;
  /**
   * multiple_choice: the choices. reorder: shuffled English chunks.
   * find_error: the words of the sentence in order. Empty for the other types.
   */
  options: string[];
  /** One Italian sentence about the story of the topic. It can be empty. */
  context: string;
}

export type Verdict = 'correct' | 'partial' | 'wrong';

export interface Solution {
  model_answer: string;
  /** The answer of the student, corrected. Null when there is nothing to correct. */
  corrected: string | null;
  explanation: string;
}

export interface AttemptFeedback {
  /** 1, 2, 3... */
  attempt: number;
  verdict: Verdict;
  score: number;
  /** Italian text, specific to this attempt. It can contain markdown. */
  feedback: string;
  /** Italian hint without the solution. Null when correct or done. */
  hint: string | null;
  errors: string[];
  /** Format: `<topic_id>#<section-slug>`. */
  rule_ref: string;
  /** True when correct, or after the third attempt. */
  done: boolean;
  /** Present when done. */
  solution: Solution | null;
}

/** One answer of the student with the feedback of the Tutor. */
export interface Attempt {
  answer: string;
  feedback: AttemptFeedback;
}

export interface ExplainSource {
  /** Format: `<topic_id>#<section-slug>`. */
  rule_ref: string;
  title: string;
}

/** A new explanation of a topic that the Tutor writes (markdown, Italian). */
export interface Explanation {
  explanation: string;
  sources: ExplainSource[];
}

export interface TopicStats {
  topic_id: string;
  attempts: number;
  correct: number;
  accuracy: number;
}

export interface TopicMemory {
  strengths: string[];
  weaknesses: string[];
  next_focus: string;
  story_so_far: string;
  updated_at: string;
}

export interface LearnerProfile {
  topics: TopicStats[];
  /** The number of wrong answers for each `rule_ref`. */
  frequent_errors: Record<string, number>;
  streak_days: number;
  /** ISO dates (YYYY-MM-DD) of the last 30 days with at least one attempt. */
  active_days: string[];
  /** What the Tutor remembers about the student, for each topic id. */
  memories: Record<string, TopicMemory>;
}
