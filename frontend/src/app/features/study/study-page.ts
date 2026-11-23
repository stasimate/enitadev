import { Component, effect, inject, Injector, signal } from '@angular/core';
import { ExplainPanel } from '../explain/explain-panel/explain-panel';
import { PracticePanel } from '../practice/practice-panel/practice-panel';
import { scrollToSection } from '../theory/scroll-to-section';
import { TheoryCard } from '../theory/theory-card/theory-card';
import { TheoryStore } from '../theory/theory-store';
import { TopicSelect } from '../theory/topic-select/topic-select';

type Pane = 'theory' | 'practice';

/** The study page: the split screen with the theory and the practice. */
@Component({
  selector: 'en-study-page',
  imports: [TopicSelect, TheoryCard, PracticePanel, ExplainPanel],
  host: { class: 'flex flex-1 flex-col' },
  templateUrl: './study-page.html',
})
export class StudyPage {
  protected readonly theory = inject(TheoryStore);

  /** The active pane on small screens. Below `lg`, the two panes are tabs. */
  protected readonly activePane = signal<Pane>('theory');

  private readonly injector = inject(Injector);

  constructor() {
    // A rule can be highlighted before the card loads (link from the progress page).
    effect(() => {
      const slug = this.theory.highlighted();
      const card = this.theory.card.hasValue() ? this.theory.card.value() : null;
      if (slug && card?.id === this.theory.selectedId()) scrollToSection(slug, this.injector);
    });
  }

  /** Show the theory pane and scroll to the highlighted section. */
  protected revealRule(): void {
    this.activePane.set('theory');
    scrollToSection(this.theory.highlighted(), this.injector);
  }
}
