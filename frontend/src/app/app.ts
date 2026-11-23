import { afterNextRender, Component, inject, Injector, signal } from '@angular/core';
import { PracticePanel } from './features/practice/practice-panel/practice-panel';
import { TheoryCard } from './features/theory/theory-card/theory-card';
import { TheoryStore } from './features/theory/theory-store';
import { TopicSelect } from './features/theory/topic-select/topic-select';

type Pane = 'theory' | 'practice';

/** The application shell: header and split-screen layout. */
@Component({
  selector: 'en-root',
  imports: [TopicSelect, TheoryCard, PracticePanel],
  templateUrl: './app.html',
})
export class App {
  protected readonly theory = inject(TheoryStore);

  /** The active pane on small screens. Below `lg`, the two panes are tabs. */
  protected readonly activePane = signal<Pane>('theory');

  private readonly injector = inject(Injector);

  /** Show the theory pane and scroll to the highlighted section. */
  protected revealRule(): void {
    this.activePane.set('theory');
    afterNextRender(
      () => {
        const slug = this.theory.highlighted();
        document.getElementById(`sec-${slug}`)?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
      },
      { injector: this.injector },
    );
  }
}
