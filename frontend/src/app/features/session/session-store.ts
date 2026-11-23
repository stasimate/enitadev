import { computed, effect, inject, Service, signal, untracked } from '@angular/core';
import { Exercise } from '../../core/models';
import { Outcome, PracticeStore } from '../practice/practice-store';
import { TheoryStore } from '../theory/theory-store';

export const SESSION_SIZE = 10;

export interface SessionResult extends Outcome {
  exercise: Exercise;
}

/** State of a session of 10 exercises. It counts each exercise that the practice store closes. */
@Service()
export class SessionStore {
  private readonly practice = inject(PracticeStore);
  private readonly theory = inject(TheoryStore);
  private lastClosed: Exercise | null = null;

  readonly size = SESSION_SIZE;
  readonly active = signal(false);
  readonly results = signal<SessionResult[]>([]);

  /** True when the student answered all the exercises. */
  readonly finished = computed(() => this.active() && this.results().length >= this.size);
  private readonly summaryRequested = signal(false);
  /** The summary shows after the student read the last feedback. */
  readonly summaryOpen = computed(() => this.finished() && this.summaryRequested());
  readonly correct = computed(
    () => this.results().filter((r) => r.verdict === 'correct').length,
  );
  /** The final verdict counts. Only `correct` is a success, in any attempt. */
  readonly wrong = computed(() => this.results().filter((r) => r.verdict !== 'correct'));
  /** The number of the exercise on screen, from 1 to size. */
  readonly position = computed(() => {
    const done = this.results().length;
    return Math.min(this.practice.status() === 'done' ? done : done + 1, this.size);
  });
  /** True when the student can ask for the next exercise. */
  readonly canContinue = computed(
    () => this.active() && !this.finished() && this.practice.status() === 'done',
  );

  constructor() {
    // A new topic ends the session.
    effect(() => {
      this.theory.selectedId();
      untracked(() => this.close());
    });
    // Each closed exercise is one result. An open exercise or a retry is not counted.
    effect(() => {
      const closed = this.practice.status() === 'done';
      const outcome = this.practice.outcome();
      untracked(() => this.record(closed, outcome));
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

  private record(closed: boolean, outcome: Outcome): void {
    const exercise = this.practice.exercise();
    if (!closed || !exercise || exercise === this.lastClosed) return;
    this.lastClosed = exercise;
    if (!this.active() || this.finished()) return;
    this.results.update((r) => [...r, { exercise, ...outcome }]);
  }
}
