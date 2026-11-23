import { Component, computed, input, output, signal } from '@angular/core';
import { WRITING_MAX_LENGTH } from '../../../core/models';

/** A text area for a free text answer. Ctrl+Enter or Cmd+Enter sends it. */
@Component({
  selector: 'en-writing-input',
  template: `
    <form class="flex flex-col gap-3" (submit)="submit($event)">
      <label class="flex flex-col gap-1 text-sm font-bold uppercase">
        {{ label() }}
        <textarea
          rows="5"
          [attr.maxlength]="maxLength"
          class="resize-y border-2 border-ink bg-paper px-3 py-2 text-base font-normal normal-case"
          [value]="text()"
          [disabled]="disabled()"
          (input)="text.set($any($event.target).value)"
          (keydown)="onKeydown($event)"
        ></textarea>
      </label>
      <div class="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          class="border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
          [disabled]="!canSubmit()"
        >
          [ Invia ]
        </button>
        <span class="text-sm" aria-live="off">{{ text().length }}/{{ maxLength }}</span>
        <span class="text-xs">CTRL/CMD + INVIO</span>
      </div>
    </form>
  `,
})
export class WritingInput {
  readonly label = input('La tua risposta');
  /** True while the backend checks the answer. */
  readonly disabled = input(false);
  readonly answered = output<string>();

  protected readonly maxLength = WRITING_MAX_LENGTH;
  protected readonly text = signal('');
  protected readonly canSubmit = computed(
    () => !this.disabled() && !!this.text().trim() && this.text().length <= this.maxLength,
  );

  protected submit(event?: Event): void {
    event?.preventDefault();
    if (this.canSubmit()) this.answered.emit(this.text().trim());
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) this.submit(event);
  }
}
