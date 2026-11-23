import { Component, input, output, signal } from '@angular/core';
import { Exercise } from '../../../core/models';

/** Collects the answer: a text input for fill_blank, one button for each option otherwise. */
@Component({
  selector: 'en-answer-form',
  template: `
    @if (exercise().type === 'multiple_choice') {
      <div class="flex flex-col gap-2" role="group" aria-label="Scegli la risposta">
        @for (option of exercise().options; track option) {
          <button
            type="button"
            class="border-2 border-ink px-4 py-2 text-left font-bold shadow-brutal-sm hover:bg-ink hover:text-paper disabled:opacity-60"
            [disabled]="disabled()"
            (click)="answered.emit(option)"
          >
            {{ option }}
          </button>
        }
      </div>
    } @else {
      <form class="flex flex-col gap-3" (submit)="submit($event)">
        <label class="flex flex-col gap-1 text-sm font-bold uppercase">
          La tua risposta
          <input
            type="text"
            maxlength="300"
            autocomplete="off"
            class="border-2 border-ink bg-paper px-3 py-2 text-base font-normal normal-case"
            [value]="text()"
            [disabled]="disabled()"
            (input)="text.set($any($event.target).value)"
          />
        </label>
        <button
          type="submit"
          class="self-start border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
          [disabled]="disabled() || !text().trim()"
        >
          [ Verifica ]
        </button>
      </form>
    }
  `,
})
export class AnswerForm {
  readonly exercise = input.required<Exercise>();
  /** True while the backend checks the answer. */
  readonly disabled = input(false);
  readonly answered = output<string>();

  protected readonly text = signal('');

  protected submit(event: Event): void {
    event.preventDefault();
    const value = this.text().trim();
    if (value && !this.disabled()) this.answered.emit(value);
  }
}
