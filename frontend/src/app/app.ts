import { Component, inject, signal } from '@angular/core';
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
}
