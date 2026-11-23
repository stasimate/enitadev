import { Component, input, output } from '@angular/core';

/** Shows the words of a sentence. A click on a word is the answer. */
@Component({
  selector: 'en-word-picker',
  template: `
    <div class="flex flex-wrap gap-2" role="group" aria-label="Scegli la parola sbagliata">
      @for (word of words(); track $index) {
        <button
          type="button"
          class="border-2 border-ink px-3 py-1 text-lg font-bold shadow-brutal-sm hover:bg-ink hover:text-paper disabled:opacity-60"
          [disabled]="disabled()"
          (click)="answered.emit(word)"
        >
          {{ word }}
        </button>
      }
    </div>
  `,
})
export class WordPicker {
  readonly words = input.required<string[]>();
  readonly disabled = input(false);
  readonly answered = output<string>();
}
