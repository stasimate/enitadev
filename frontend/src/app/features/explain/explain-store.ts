import { HttpErrorResponse } from '@angular/common/http';
import { effect, inject, Service, signal, untracked } from '@angular/core';
import { Subscription } from 'rxjs';
import { Api } from '../../core/api';
import { ExplainSource } from '../../core/models';
import { TheoryStore } from '../theory/theory-store';

export type ExplainStatus = 'idle' | 'loading' | 'ready' | 'error';

/** State of "Spiegami meglio": the new explanation of the selected topic. */
@Service()
export class ExplainStore {
  private readonly api = inject(Api);
  private readonly theory = inject(TheoryStore);
  private pending: Subscription | null = null;

  readonly status = signal<ExplainStatus>('idle');
  /** Markdown text in Italian. */
  readonly explanation = signal<string | null>(null);
  readonly sources = signal<ExplainSource[]>([]);
  readonly error = signal<string | null>(null);
  /** True when the request failed with a temporary error (502, 504). */
  readonly retryable = signal(false);

  constructor() {
    // A new topic makes the old explanation useless.
    effect(() => {
      this.theory.selectedId();
      untracked(() => this.reset());
    });
  }

  /** Ask for the explanation of the selected topic. Also used to retry. */
  explain(): void {
    const topicId = this.theory.selectedId();
    if (!topicId || this.status() === 'loading') return;
    this.error.set(null);
    this.retryable.set(false);
    this.status.set('loading');
    this.pending = this.api.explain(topicId).subscribe({
      next: (result) => {
        this.explanation.set(result.explanation);
        this.sources.set(result.sources);
        this.status.set('ready');
      },
      error: (err: unknown) => this.fail(err),
    });
  }

  private reset(): void {
    this.pending?.unsubscribe();
    this.pending = null;
    this.explanation.set(null);
    this.sources.set([]);
    this.error.set(null);
    this.retryable.set(false);
    this.status.set('idle');
  }

  private fail(err: unknown): void {
    const status = err instanceof HttpErrorResponse ? err.status : 0;
    this.explanation.set(null);
    this.sources.set([]);
    this.retryable.set(status === 502 || status === 504);
    this.error.set(this.messageFor(err, status));
    this.status.set('error');
  }

  private messageFor(err: unknown, status: number): string {
    if (status === 502) return 'Il Tutor non è riuscito a preparare la spiegazione.';
    if (status === 504) return 'Il Tutor ci mette troppo tempo.';
    if (status === 503) {
      const detail: unknown = (err as HttpErrorResponse).error?.detail;
      return typeof detail === 'string' && detail
        ? detail
        : 'Il provider IA ha rifiutato la richiesta. Controlla la chiave API nel file .env.';
    }
    return 'Il backend non risponde.';
  }
}
