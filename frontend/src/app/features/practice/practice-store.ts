import { HttpErrorResponse } from '@angular/common/http';
import { computed, effect, inject, Service, signal, untracked } from '@angular/core';
import { Subscription } from 'rxjs';
import { Api } from '../../core/api';
import { Attempt, Exercise, Solution, Verdict } from '../../core/models';
import { TheoryStore } from '../theory/theory-store';

/** `answering`: the exercise is open. `done`: the exercise is closed (the thread is final). */
export type PracticeStatus = 'idle' | 'loading' | 'answering' | 'checking' | 'done' | 'error';

/** The final result of an exercise. */
export interface Outcome {
  attempts: number;
  verdict: Verdict;
  /** The rule of the last attempt. Null when the student did not answer. */
  ruleRef: string | null;
}

/** State of the practice part: the exercise, the thread of attempts and the request status. */
@Service()
export class PracticeStore {
  private readonly api = inject(Api);
  private readonly theory = inject(TheoryStore);
  private pending: Subscription | null = null;
  private lastTopicId: string | null = null;

  readonly exercise = signal<Exercise | null>(null);
  /** The answers of the student for this exercise, the oldest first. */
  readonly attempts = signal<Attempt[]>([]);
  private readonly shownSolution = signal<Solution | null>(null);
  readonly status = signal<PracticeStatus>('idle');
  readonly error = signal<string | null>(null);
  /** True when the last exercise request failed with a temporary error (502, 504). */
  readonly retryable = signal(false);

  /** The feedback of the last attempt. */
  readonly feedback = computed(() => this.attempts().at(-1)?.feedback ?? null);
  /** The solution: from the button, or from the feedback that closed the exercise. */
  readonly solution = computed(() => this.shownSolution() ?? this.feedback()?.solution ?? null);
  /** The result of the exercise. It is meaningful when the status is `done`. */
  readonly outcome = computed<Outcome>(() => {
    const attempts = this.attempts();
    const last = attempts.at(-1)?.feedback;
    const correct = attempts.some((a) => a.feedback.verdict === 'correct');
    return {
      attempts: attempts.length,
      verdict: correct ? 'correct' : (last?.verdict ?? 'wrong'),
      ruleRef: last?.rule_ref ?? null,
    };
  });
  /** True when the student can ask for the solution. */
  readonly canShowSolution = computed(() => {
    const last = this.feedback();
    return this.status() === 'answering' && !!last && !last.done;
  });

  constructor() {
    // A new topic makes the old exercise useless.
    effect(() => {
      this.theory.selectedId();
      const topicId = this.theory.selectedId();
      untracked(() => {
        this.reset();
        // Warm up the backend. The result does not matter.
        if (topicId) this.api.prefetch(topicId).subscribe({ error: () => undefined });
      });
    });
  }

  newExercise(topicId: string): void {
    this.pending?.unsubscribe();
    this.lastTopicId = topicId;
    this.retryable.set(false);
    this.exercise.set(null);
    this.clearThread();
    this.error.set(null);
    this.status.set('loading');
    this.pending = this.api.createExercise(topicId).subscribe({
      next: (exercise) => {
        this.exercise.set(exercise);
        this.status.set('answering');
      },
      error: (err: unknown) => this.fail(err),
    });
  }

  submit(answer: string): void {
    const exercise = this.exercise();
    if (!exercise || this.status() !== 'answering') return;
    this.error.set(null);
    this.status.set('checking');
    this.pending = this.api.answerExercise(exercise.id, answer).subscribe({
      next: (feedback) => {
        this.attempts.update((list) => [...list, { answer, feedback }]);
        // A feedback that is not done keeps the exercise open for a new attempt.
        this.status.set(feedback.done ? 'done' : 'answering');
      },
      error: (err: unknown) => this.fail(err, 'answering'),
    });
  }

  /** Close the exercise and show the solution. */
  showSolution(): void {
    const exercise = this.exercise();
    if (!exercise || !this.canShowSolution()) return;
    this.error.set(null);
    this.status.set('checking');
    this.pending = this.api.solution(exercise.id).subscribe({
      next: (solution) => {
        this.shownSolution.set(solution);
        this.status.set('done');
      },
      error: (err: unknown) => this.fail(err, 'answering'),
    });
  }

  /** Ask again for the exercise that failed with a temporary error. */
  retry(): void {
    if (this.retryable() && this.lastTopicId) this.newExercise(this.lastTopicId);
  }

  /** Highlight a theory section. Default: the rule of the feedback. Only for the topic on screen. */
  showRule(ruleRef: string | undefined = this.outcome().ruleRef ?? undefined): void {
    const ref = ruleRef;
    if (!ref) return;
    const [topicId, slug] = ref.split('#');
    if (slug && topicId === this.theory.selectedId()) this.theory.highlighted.set(slug);
  }

  private reset(): void {
    this.pending?.unsubscribe();
    this.pending = null;
    this.exercise.set(null);
    this.clearThread();
    this.error.set(null);
    this.retryable.set(false);
    this.status.set('idle');
  }

  private clearThread(): void {
    this.attempts.set([]);
    this.shownSolution.set(null);
  }

  /**
   * A rejected answer lets the student try again. A failed exercise does not.
   * A 409 means that the exercise is closed.
   */
  private fail(err: unknown, next: 'error' | 'answering' = 'error'): void {
    const status = err instanceof HttpErrorResponse ? err.status : 0;
    this.error.set(this.messageFor(err));
    if (next === 'answering' && status === 409) {
      this.retryable.set(false);
      this.status.set('done');
      return;
    }
    // Only a failed exercise request with a temporary cause can be retried.
    this.retryable.set(next === 'error' && (status === 502 || status === 504));
    this.status.set(next);
  }

  private messageFor(err: unknown): string {
    const status = err instanceof HttpErrorResponse ? err.status : 0;
    if (status === 502) return 'Il Tutor non è riuscito a creare un esercizio.';
    if (status === 504) return 'Il Tutor ci mette troppo tempo.';
    if (status === 409) return 'Questo esercizio è già chiuso.';
    if (status === 503)
      return 'Il provider IA ha rifiutato la richiesta. Controlla la chiave API nel file .env.';
    if (status === 422) {
      const detail: unknown = (err as HttpErrorResponse).error?.detail;
      return typeof detail === 'string' && detail ? detail : 'Risposta non valida.';
    }
    return 'Il backend non risponde.';
  }
}
