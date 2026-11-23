import { Component, input, output } from '@angular/core';
import { Verdict } from '../../../core/models';
import { SessionResult } from '../session-store';

/** Shows the score of a finished session. Each exercise has its attempts and verdict. The wrong ones have their rule. */
@Component({
  selector: 'en-session-summary',
  template: `
    <section class="flex flex-col gap-4" aria-labelledby="summary-title">
      <h3 id="summary-title" class="text-sm font-bold uppercase">// Risultato</h3>
      <p class="text-4xl font-bold">{{ correct() }}/{{ total() }}</p>
      <ul class="flex flex-col gap-3">
        @for (item of results(); track $index) {
          <li class="flex flex-col gap-1 border-2 border-ink p-3">
            <p>{{ item.exercise.prompt }}</p>
            <p class="text-sm font-bold uppercase">
              {{ item.attempts }} {{ item.attempts === 1 ? 'tentativo' : 'tentativi' }} ·
              <span [class.text-ok]="item.verdict === 'correct'" [class.text-err]="item.verdict === 'wrong'">{{
                labels[item.verdict]
              }}</span>
            </p>
            @if (item.verdict !== 'correct' && item.ruleRef; as ruleRef) {
              <p class="text-sm">Regola: {{ ruleRef }}</p>
              <button
                type="button"
                class="self-start border-2 border-ink px-3 py-1 font-bold uppercase shadow-brutal-sm"
                (click)="showRule.emit(ruleRef)"
              >
                [ Vedi la regola ]
              </button>
            }
          </li>
        }
      </ul>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm"
          (click)="restart.emit()"
        >
          [ Nuova sessione ]
        </button>
        <button
          type="button"
          class="border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm"
          (click)="closed.emit()"
        >
          [ Chiudi ]
        </button>
      </div>
    </section>
  `,
})
export class SessionSummary {
  readonly correct = input.required<number>();
  readonly total = input.required<number>();
  readonly results = input.required<SessionResult[]>();
  readonly showRule = output<string>();
  readonly restart = output<void>();
  readonly closed = output<void>();

  protected readonly labels: Record<Verdict, string> = {
    correct: 'CORRETTO',
    partial: 'PARZIALE',
    wrong: 'SBAGLIATO',
  };
}
