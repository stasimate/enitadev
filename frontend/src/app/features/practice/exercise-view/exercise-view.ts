import { Component, computed, input } from '@angular/core';
import { Exercise } from '../../../core/models';

/** Shows the instruction and the prompt of one exercise. The blank is a visible box. */
@Component({
  selector: 'en-exercise-view',
  template: `
    <div class="flex flex-col gap-2">
      <p class="text-sm font-bold uppercase">// {{ exercise().instruction }}</p>
      <p class="text-lg leading-loose">
        @for (part of parts(); track $index) {
          @if ($index > 0) {
            <span
              class="mx-1 inline-block min-w-16 border-b-2 border-ink bg-ink/10 align-middle"
              role="img"
              aria-label="spazio da completare"
              >&nbsp;</span
            >
          }
          {{ part }}
        }
      </p>
    </div>
  `,
})
export class ExerciseView {
  readonly exercise = input.required<Exercise>();

  /** The prompt split at each blank. */
  protected readonly parts = computed(() => this.exercise().prompt.split('___'));
}
