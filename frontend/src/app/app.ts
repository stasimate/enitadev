import { ChangeDetectionStrategy, Component, signal } from '@angular/core';

type Pane = 'theory' | 'practice';

@Component({
  selector: 'en-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.html',
})
export class App {
  /** Active pane on small screens (below lg both panes are stacked as tabs). */
  protected readonly activePane = signal<Pane>('theory');
}
