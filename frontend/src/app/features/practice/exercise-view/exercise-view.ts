import { Component, computed, input } from '@angular/core';
import { Exercise } from '../../../core/models';

/** Shows the instruction and the prompt of one exercise. The prompt depends on the type. */
@Component({
  selector: 'en-exercise-view',
  template: `
    <div class="flex flex-col gap-2">
      @if (exercise().context) {
        <p class="text-sm italic">// STORIA: {{ exercise().context }}</p>
      }
      <p class="text-sm font-bold uppercase">// {{ exercise().instruction }}</p>
      @switch (exercise().type) {
        @case ('reorder') {
          <p class="text-lg leading-loose">IT: {{ exercise().prompt }}</p>
        }
        @case ('translate') {
          <p class="border-l-4 border-ink pl-3 text-lg leading-loose">IT: {{ exercise().prompt }}</p>
        }
        @case ('guided') {
          <p class="border-l-4 border-ink pl-3 text-lg leading-loose">{{ exercise().prompt }}</p>
        }
        @case ('rewrite') {
          <p class="border-l-4 border-ink pl-3 text-lg leading-loose">{{ exercise().prompt }}</p>
        }
        @case ('dialogue') {
          <p class="border-l-4 border-ink pl-3 text-lg leading-loose">{{ exercise().prompt }}</p>
        }
        @case ('transform') {
          <p class="border-l-4 border-ink pl-3 text-lg leading-loose">{{ exercise().prompt }}</p>
        }
        @case ('find_error') {
          <!-- The words are in the picker. -->
        }
        @default {
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
        }
      }
    </div>
  `,
})
export class ExerciseView {
  readonly exercise = input.required<Exercise>();

  /** The prompt split at each blank. */
  protected readonly parts = computed(() => this.exercise().prompt.split('___'));
}
