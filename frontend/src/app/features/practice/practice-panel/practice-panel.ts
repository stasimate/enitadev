import { Component, input } from '@angular/core';

/** The practice part. Milestone M2 adds the exercises and the AI feedback. */
@Component({
  selector: 'en-practice-panel',
  template: `
    <div class="border-2 border-ink p-4 shadow-brutal">
      <p class="mb-4">
        @if (topicTitle(); as title) {
          Esercizi su <strong>{{ title }}</strong>: arrivano con il Tutor IA.
        } @else {
          Scegli un argomento per iniziare.
        }
      </p>
      <button
        type="button"
        disabled
        class="border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
      >
        [ Nuovo esercizio ]
      </button>
    </div>
  `,
})
export class PracticePanel {
  readonly topicTitle = input<string | null>(null);
}
