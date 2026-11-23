import { Component, input } from '@angular/core';
import { TopicCard } from '../../../core/models';
import { Speakable } from '../../../shared/directives/speakable';
import { MarkdownPipe } from '../../../shared/pipes/markdown-pipe';

/** Shows one theory card. Projected content shows under the title. It highlights the section that the feedback refers to. */
@Component({
  selector: 'en-theory-card',
  imports: [MarkdownPipe, Speakable],
  template: `
    <article class="flex flex-col gap-4">
      <header class="flex items-baseline justify-between gap-4">
        <h3 class="text-2xl font-bold">{{ card().title }}</h3>
        <span class="border-2 border-ink px-2 text-sm font-bold">{{ card().level }}</span>
      </header>
      <ng-content />
      @for (section of card().sections; track section.slug) {
        <section
          [id]="'sec-' + section.slug"
          class="border-2 p-4"
          [class.border-ink]="section.slug !== highlighted()"
          [class.shadow-brutal]="section.slug !== highlighted()"
          [class.border-accent]="section.slug === highlighted()"
          [class.shadow-brutal-accent]="section.slug === highlighted()"
          [attr.aria-current]="section.slug === highlighted() ? 'true' : null"
        >
          <h4 class="mb-2 text-sm font-bold uppercase">// {{ section.title }}</h4>
          <div class="md" [enSpeakable]="section.markdown" [innerHTML]="section.markdown | markdown"></div>
        </section>
      }
    </article>
  `,
})
export class TheoryCard {
  readonly card = input.required<TopicCard>();
  readonly highlighted = input<string | null>(null);
}
