import { Component, input, output } from '@angular/core';
import { Solution } from '../../../core/models';
import { MarkdownPipe } from '../../../shared/pipes/markdown-pipe';

/** Shows the solution of a closed exercise. It can ask for the rule. */
@Component({
  selector: 'en-solution-view',
  imports: [MarkdownPipe],
  template: `
    <section class="flex flex-col gap-3 border-2 border-ink p-4 shadow-brutal">
      <h3 class="text-sm font-bold uppercase">// Soluzione</h3>
      <div>
        <p class="text-sm font-bold uppercase">Risposta modello</p>
        <p class="whitespace-pre-wrap">{{ solution().model_answer }}</p>
      </div>
      @if (solution().corrected; as corrected) {
        <div>
          <p class="text-sm font-bold uppercase">La tua risposta corretta</p>
          <p class="whitespace-pre-wrap">{{ corrected }}</p>
        </div>
      }
      <div class="md" [innerHTML]="solution().explanation | markdown"></div>
      @if (ruleRef()) {
        <button
          type="button"
          class="self-start border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm"
          (click)="showRule.emit()"
        >
          [ Vedi la regola ]
        </button>
      }
    </section>
  `,
})
export class SolutionView {
  readonly solution = input.required<Solution>();
  /** The rule to show. Without a rule, there is no button. */
  readonly ruleRef = input<string | null>(null);
  readonly showRule = output<void>();
}
