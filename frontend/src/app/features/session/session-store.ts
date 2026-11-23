import { computed, effect, inject, Service, signal, untracked } from '@angular/core';
import { Exercise, Feedback } from '../../core/models';
import { PracticeStore } from '../practice/practice-store';
import { TheoryStore } from '../theory/theory-store';

export const SESSION_SIZE = 10;

export interface SessionResult {
  exercise: Exercise;
  feedback: Feedback;
}

/** State of a session of 10 exercises. It counts the feedback of the practice store. */
@Service()
export class SessionStore {
  private readonly practice = inject(PracticeStore);
  private readonly theory = inject(TheoryStore);
  private lastFeedback: Feedback | null = null;

  readonly size = SESSION_SIZE;
  readonly active = signal(false);
  readonly results = signal<SessionResult[]>([]);

  /** True when the student answered all the exercises. */
  readonly finished = computed(() => this.active() && this.results().length >= this.size);
  private readonly summaryRequested = signal(false);
  /** The summary shows after the student read the last feedback. */
  readonly summaryOpen = computed(() => this.finished() && this.summaryRequested());
  readonly correct = computed(
    () => this.results().filter((r) => r.feedback.verdict === 'correct').length,
  );
  /** Only a `correct` verdict counts. `partial` and `wrong` do not. */
  readonly wrong = computed(() => this.results().filter((r) => r.feedback.verdict !== 'correct'));
  /** The number of the exercise on screen, from 1 to size. */
  readonly position = computed(() => {
    const done = this.results().length;
    return Math.min(this.practice.status() === 'feedback' ? done : done + 1, this.size);
  });
  /** True when the student can ask for the next exercise. */
  readonly canContinue = computed(
    () => this.active() && !this.finished() && this.practice.status() === 'feedback',
  );

  constructor() {
    // A new topic ends the session.
    effect(() => {
      this.theory.selectedId();
      untracked(() => this.close());
    });
    // Each new feedback is one exercise. A retry makes no feedback, so it is not counted.
    effect(() => {
      const feedback = this.practice.feedback();
      untracked(() => this.record(feedback));
    });
  }

  start(): void {
    const topicId = this.theory.selectedId();
    if (!topicId) return;
    this.results.set([]);
    this.summaryRequested.set(false);
    this.active.set(true);
    this.practice.newExercise(topicId);
  }

  next(): void {
    const topicId = this.theory.selectedId();
    if (topicId && this.canContinue()) this.practice.newExercise(topicId);
  }

  showSummary(): void {
    if (this.finished()) this.summaryRequested.set(true);
  }

  close(): void {
    this.summaryRequested.set(false);
    this.active.set(false);
    this.results.set([]);
  }

  private record(feedback: Feedback | null): void {
    const exercise = this.practice.exercise();
    if (!feedback || feedback === this.lastFeedback) return;
    this.lastFeedback = feedback;
    if (!this.active() || !exercise || this.finished()) return;
    this.results.update((r) => [...r, { exercise, feedback }]);
  }
}
