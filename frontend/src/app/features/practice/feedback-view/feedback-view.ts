import { Component, computed, input } from '@angular/core';
import { Attempt, Verdict } from '../../../core/models';
import { MarkdownPipe } from '../../../shared/pipes/markdown-pipe';

const LABELS: Record<Verdict, string> = {
  correct: 'CORRETTO',
  partial: 'PARZIALE',
  wrong: 'SBAGLIATO',
};

/** Shows one attempt of the thread: the answer, the verdict, the feedback, the errors and the hint. */
@Component({
  selector: 'en-feedback-view',
  imports: [MarkdownPipe],
  template: `
    <article class="flex flex-col gap-3 border-2 border-ink p-4" [attr.aria-label]="title()">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-sm font-bold uppercase">// {{ title() }}</h3>
        <span
          class="inline-block border-2 px-2 py-1 font-bold"
          [class.border-ok]="verdict() === 'correct'"
          [class.text-ok]="verdict() === 'correct'"
          [class.border-err]="verdict() === 'wrong'"
          [class.text-err]="verdict() === 'wrong'"
          [class.border-accent]="verdict() === 'partial'"
          [class.text-ink]="verdict() === 'partial'"
          >{{ label() }}</span
        >
      </div>
      <p class="whitespace-pre-wrap border-l-4 border-ink pl-3">{{ attempt().answer }}</p>
      <div class="md" [innerHTML]="attempt().feedback.feedback | markdown"></div>
      @if (attempt().feedback.errors.length) {
        <ul class="flex flex-col gap-1 text-err" aria-label="Errori">
          @for (error of attempt().feedback.errors; track $index) {
            <li>[ ERRORE ] {{ error }}</li>
          }
        </ul>
      }
      @if (attempt().feedback.hint; as hint) {
        <p><span class="text-sm font-bold uppercase">// Suggerimento</span> {{ hint }}</p>
      }
    </article>
  `,
})
export class FeedbackView {
  readonly attempt = input.required<Attempt>();

  protected readonly verdict = computed(() => this.attempt().feedback.verdict);
  protected readonly label = computed(() => LABELS[this.verdict()]);
  protected readonly title = computed(() => `Tentativo ${this.attempt().feedback.attempt}`);
}
