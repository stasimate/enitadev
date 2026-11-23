import { Component, computed, input, linkedSignal, output } from '@angular/core';

/** Builds a sentence from chunks. The student clicks the chunks in order. */
@Component({
  selector: 'en-reorder-input',
  template: `
    <div class="flex flex-col gap-3">
      <p class="min-h-12 border-2 border-ink p-2" aria-live="polite" aria-label="Frase costruita">
        @for (word of built(); track $index) {
          <span class="mr-2 inline-block border-b-2 border-accent font-bold">{{ word }}</span>
        } @empty {
          <span class="opacity-70">Tocca i pezzi nell'ordine giusto.</span>
        }
      </p>
      <div class="flex flex-wrap gap-2" role="group" aria-label="Pezzi della frase">
        @for (chunk of chunks(); track $index) {
          <button
            type="button"
            class="border-2 border-ink px-3 py-1 font-bold shadow-brutal-sm hover:bg-ink hover:text-paper disabled:line-through disabled:opacity-60"
            [disabled]="disabled() || picked().includes($index)"
            (click)="pick($index)"
          >
            {{ chunk }}
          </button>
        }
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
          [disabled]="disabled() || !picked().length"
          (click)="undo()"
        >
          [ Annulla ]
        </button>
        <button
          type="button"
          class="border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
          [disabled]="disabled() || !picked().length"
          (click)="reset()"
        >
          [ Ricomincia ]
        </button>
        <button
          type="button"
          class="border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
          [disabled]="disabled() || !complete()"
          (click)="submit()"
        >
          [ Verifica ]
        </button>
      </div>
    </div>
  `,
})
export class ReorderInput {
  readonly chunks = input.required<string[]>();
  readonly disabled = input(false);
  /** The built sentence: the chunks joined with one space. */
  readonly answered = output<string>();

  /** Indexes of the used chunks, in click order. Index tracking handles duplicate chunks. */
  protected readonly picked = linkedSignal<string[], number[]>({
    source: this.chunks,
    computation: () => [],
  });

  protected readonly built = computed(() => this.picked().map((i) => this.chunks()[i]));
  protected readonly complete = computed(
    () => this.chunks().length > 0 && this.picked().length === this.chunks().length,
  );

  protected pick(index: number): void {
    if (!this.picked().includes(index)) this.picked.update((p) => [...p, index]);
  }

  protected undo(): void {
    this.picked.update((p) => p.slice(0, -1));
  }

  protected reset(): void {
    this.picked.set([]);
  }

  protected submit(): void {
    if (this.complete() && !this.disabled()) this.answered.emit(this.built().join(' '));
  }
}
