import { HttpErrorResponse } from '@angular/common/http';
import { effect, inject, Service, signal, untracked } from '@angular/core';
import { Subscription } from 'rxjs';
import { Api } from '../../core/api';
import { Exercise, Feedback } from '../../core/models';
import { TheoryStore } from '../theory/theory-store';

export type PracticeStatus = 'idle' | 'loading' | 'answering' | 'checking' | 'feedback' | 'error';

/** State of the practice part: the exercise, the feedback and the request status. */
@Service()
export class PracticeStore {
  private readonly api = inject(Api);
  private readonly theory = inject(TheoryStore);
  private pending: Subscription | null = null;
  private lastTopicId: string | null = null;

  readonly exercise = signal<Exercise | null>(null);
  readonly feedback = signal<Feedback | null>(null);
  readonly status = signal<PracticeStatus>('idle');
  readonly error = signal<string | null>(null);
  /** True when the last exercise request failed with a temporary error (502, 504). */
  readonly retryable = signal(false);

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
    this.feedback.set(null);
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
        this.feedback.set(feedback);
        this.status.set('feedback');
      },
      error: (err: unknown) => this.fail(err, 'answering'),
    });
  }

  /** Ask again for the exercise that failed with a temporary error. */
  retry(): void {
    if (this.retryable() && this.lastTopicId) this.newExercise(this.lastTopicId);
  }

  /** Highlight a theory section. Default: the rule of the feedback. Only for the topic on screen. */
  showRule(ruleRef: string | undefined = this.feedback()?.rule_ref): void {
    const ref = ruleRef;
    if (!ref) return;
    const [topicId, slug] = ref.split('#');
    if (slug && topicId === this.theory.selectedId()) this.theory.highlighted.set(slug);
  }

  private reset(): void {
    this.pending?.unsubscribe();
    this.pending = null;
    this.exercise.set(null);
    this.feedback.set(null);
    this.error.set(null);
    this.retryable.set(false);
    this.status.set('idle');
  }

  /** A rejected answer lets the student try again. A failed exercise does not. */
  private fail(err: unknown, next: 'error' | 'answering' = 'error'): void {
    const status = err instanceof HttpErrorResponse ? err.status : 0;
    this.error.set(this.messageFor(err));
    // Only a failed exercise request with a temporary cause can be retried.
    this.retryable.set(next === 'error' && (status === 502 || status === 504));
    this.status.set(next);
  }

  private messageFor(err: unknown): string {
    const status = err instanceof HttpErrorResponse ? err.status : 0;
    if (status === 502) return 'Il Tutor non è riuscito a creare un esercizio.';
    if (status === 504) return 'Il Tutor ci mette troppo tempo.';
    if (status === 503)
      return 'Il provider IA ha rifiutato la richiesta. Controlla la chiave API nel file .env.';
    if (status === 422) {
      const detail: unknown = (err as HttpErrorResponse).error?.detail;
      return typeof detail === 'string' && detail ? detail : 'Risposta non valida.';
    }
    return 'Il backend non risponde.';
  }
}
