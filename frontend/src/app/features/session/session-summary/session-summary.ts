import { Component, input, output } from '@angular/core';
import { SessionResult } from '../session-store';

/** Shows the score of a finished session and the wrong exercises with their rules. */
@Component({
  selector: 'en-session-summary',
  template: `
    <section class="flex flex-col gap-4" aria-labelledby="summary-title">
      <h3 id="summary-title" class="text-sm font-bold uppercase">// Risultato</h3>
      <p class="text-4xl font-bold">{{ correct() }}/{{ total() }}</p>
      @if (wrong().length) {
        <ul class="flex flex-col gap-3">
          @for (item of wrong(); track $index) {
            <li class="flex flex-col gap-1 border-2 border-ink p-3">
              <p>{{ item.exercise.prompt }}</p>
              <p>
                <span class="text-sm font-bold uppercase">Risposta corretta:</span>
                {{ item.feedback.correct_answer }}
              </p>
              <p class="text-sm">Regola: {{ item.feedback.rule_ref }}</p>
              <button
                type="button"
                class="self-start border-2 border-ink px-3 py-1 font-bold uppercase shadow-brutal-sm"
                (click)="showRule.emit(item.feedback.rule_ref)"
              >
                [ Vedi la regola ]
              </button>
            </li>
          }
        </ul>
      } @else {
        <p>Nessun errore. Ottimo lavoro.</p>
      }
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
  readonly wrong = input.required<SessionResult[]>();
  readonly showRule = output<string>();
  readonly restart = output<void>();
  readonly closed = output<void>();
}
