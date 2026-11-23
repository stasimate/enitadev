import { Component, computed, input, output } from '@angular/core';
import { Feedback, Verdict } from '../../../core/models';

const LABELS: Record<Verdict, string> = {
  correct: 'CORRETTO',
  partial: 'PARZIALE',
  wrong: 'SBAGLIATO',
};

/** Shows the verdict, the correct answer and the explanation. It can ask for the rule. */
@Component({
  selector: 'en-feedback-view',
  template: `
    <div aria-live="polite" class="flex flex-col gap-3">
      @if (feedback(); as fb) {
        <p>
          <span
            class="inline-block border-2 px-2 py-1 font-bold"
            [class.border-ok]="fb.verdict === 'correct'"
            [class.text-ok]="fb.verdict === 'correct'"
            [class.border-err]="fb.verdict === 'wrong'"
            [class.text-err]="fb.verdict === 'wrong'"
            [class.border-accent]="fb.verdict === 'partial'"
            [class.text-ink]="fb.verdict === 'partial'"
            >{{ label() }}</span
          >
        </p>
        <p>
          <span class="text-sm font-bold uppercase">Risposta corretta:</span>
          {{ fb.correct_answer }}
        </p>
        <p>{{ fb.explanation }}</p>
        <button
          type="button"
          class="self-start border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm"
          (click)="showRule.emit()"
        >
          [ Vedi la regola ]
        </button>
      }
    </div>
  `,
})
export class FeedbackView {
  readonly feedback = input<Feedback | null>(null);
  readonly showRule = output<void>();

  protected readonly label = computed(() => {
    const fb = this.feedback();
    return fb ? LABELS[fb.verdict] : '';
  });
}
