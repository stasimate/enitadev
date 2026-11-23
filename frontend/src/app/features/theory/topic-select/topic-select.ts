import { Component, input, model } from '@angular/core';
import { TopicGroup } from '../theory-store';

/** A native select with the topics grouped by CEFR level. */
@Component({
  selector: 'en-topic-select',
  host: { class: 'block min-w-0 max-w-full' },
  template: `
    <label class="flex w-full min-w-0 items-center gap-2 text-sm font-bold uppercase">
      <span class="shrink-0 whitespace-nowrap">[ Argomento ]</span>
      <select
        class="min-w-0 flex-1 border-2 border-ink bg-paper px-2 py-1 font-mono shadow-brutal-sm"
        [value]="selected() ?? ''"
        (change)="selected.set($any($event.target).value)"
      >
        @for (group of groups(); track group.level) {
          <optgroup [label]="group.level">
            @for (topic of group.topics; track topic.id) {
              <option [value]="topic.id" [selected]="topic.id === selected()">
                {{ topic.title }}
              </option>
            }
          </optgroup>
        }
      </select>
    </label>
  `,
})
export class TopicSelect {
  readonly groups = input.required<TopicGroup[]>();
  readonly selected = model<string | null>(null);
}
