import { Component, inject } from '@angular/core';
import { ProgressStore } from './progress-store';

/** The progress page: streak, activity of 30 days, mastery of each topic and frequent errors. */
@Component({
  selector: 'en-progress-page',
  providers: [ProgressStore],
  host: { class: 'block flex-1' },
  template: `
    <main class="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      @if (store.profile.error()) {
        <p role="alert" class="border-2 border-err p-4 text-err">
          [ ERRORE ] Il backend non risponde.
        </p>
      } @else if (!store.profile.hasValue()) {
        <p aria-live="polite">Caricamento<span class="cursor-blink">_</span></p>
      } @else {
        <section aria-labelledby="streak-title" class="flex flex-col gap-3">
          <h2 id="streak-title" class="text-sm font-bold uppercase">// Costanza</h2>
          <p class="text-2xl font-bold">STREAK: {{ store.streak() }} {{ store.streak() === 1 ? 'GIORNO' : 'GIORNI' }}</p>
          <ul class="flex flex-wrap gap-1" aria-label="Ultimi 30 giorni">
            @for (day of store.strip(); track day.date) {
              <li
                class="size-5 border-2 border-ink"
                [class.bg-accent]="day.active"
                [title]="day.date"
              >
                <span class="sr-only">{{ day.date }}: {{ day.active ? 'attivo' : 'nessuna attività' }}</span>
              </li>
            }
          </ul>
        </section>

        <section aria-labelledby="topics-title" class="flex flex-col gap-3">
          <h2 id="topics-title" class="text-sm font-bold uppercase">// Argomenti</h2>
          <ul class="flex flex-col gap-3">
            @for (row of store.rows(); track row.id) {
              <li class="flex flex-col gap-1 border-2 border-ink p-3 shadow-brutal-sm">
                <div class="flex flex-wrap items-baseline justify-between gap-2">
                  <span class="font-bold">{{ row.title }} <span class="text-sm">({{ row.level }})</span></span>
                  <span class="text-sm">
                    {{ row.correct }}/{{ row.attempts }} corrette ·
                    {{ (row.accuracy * 100).toFixed(0) }}%
                  </span>
                </div>
                <div
                  class="h-4 border-2 border-ink"
                  role="progressbar"
                  [attr.aria-label]="'Padronanza: ' + row.title"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  [attr.aria-valuenow]="(row.accuracy * 100).toFixed(0)"
                >
                  <div class="h-full bg-ok" [style.width.%]="row.accuracy * 100"></div>
                </div>
              </li>
            }
          </ul>
        </section>

        <section aria-labelledby="errors-title" class="flex flex-col gap-3">
          <h2 id="errors-title" class="text-sm font-bold uppercase">// Errori frequenti</h2>
          @if (store.errors().length === 0) {
            <p>Nessun errore. Continua così.</p>
          } @else {
            <ul class="flex flex-col gap-2">
              @for (error of store.errors(); track error.ruleRef) {
                <li
                  class="flex flex-wrap items-center justify-between gap-2 border-2 border-ink p-3"
                >
                  <span>{{ error.label }} · <strong>{{ error.count }}</strong></span>
                  <button
                    type="button"
                    class="border-2 border-ink px-3 py-1 font-bold uppercase shadow-brutal-sm"
                    (click)="store.openRule(error.ruleRef)"
                  >
                    [ Vedi la regola ]
                  </button>
                </li>
              }
            </ul>
          }
        </section>
      }
    </main>
  `,
})
export class ProgressPage {
  protected readonly store = inject(ProgressStore);
}
