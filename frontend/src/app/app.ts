import { Component, signal } from '@angular/core';

type Pane = 'theory' | 'practice';

@Component({
  selector: 'en-root',
  templateUrl: './app.html',
})
export class App {
  /** Active pane on small screens (below lg both panes are stacked as tabs). */
  protected readonly activePane = signal<Pane>('theory');
}
