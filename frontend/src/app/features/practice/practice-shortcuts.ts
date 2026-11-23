import { inject, Service } from '@angular/core';
import { SessionStore } from '../session/session-store';
import { TheoryStore } from '../theory/theory-store';
import { PracticeStore } from './practice-store';

export type Shortcut =
  | { kind: 'choose'; index: number }
  | { kind: 'new' }
  | { kind: 'next' };

/** True when the key goes to a text field. Typing must never trigger a shortcut. */
function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable;
}

/** Map a key event to a shortcut. Return null for keys that are not shortcuts. */
export function shortcutFor(
  event: Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'altKey' | 'target'>,
): Shortcut | null {
  if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return null;
  const key = event.key.toLowerCase();
  if (key >= '1' && key <= '4') return { kind: 'choose', index: Number(key) - 1 };
  if (key === 'n') return { kind: 'new' };
  if (key === 'p') return { kind: 'next' };
  return null;
}

/** Runs the keyboard shortcuts of the practice part. */
@Service()
export class PracticeShortcuts {
  private readonly practice = inject(PracticeStore);
  private readonly session = inject(SessionStore);
  private readonly theory = inject(TheoryStore);

  handle(event: KeyboardEvent): void {
    const shortcut = shortcutFor(event);
    if (!shortcut) return;
    switch (shortcut.kind) {
      case 'choose': {
        const exercise = this.practice.exercise();
        const option = exercise?.type === 'multiple_choice' ? exercise.options[shortcut.index] : null;
        if (option && this.practice.status() === 'answering') this.practice.submit(option);
        break;
      }
      case 'new': {
        const topicId = this.theory.selectedId();
        if (topicId && !this.session.active() && this.practice.status() !== 'loading') {
          this.practice.newExercise(topicId);
        }
        break;
      }
      case 'next':
        if (this.session.canContinue()) this.session.next();
        else if (this.session.finished() && this.practice.status() === 'feedback') {
          this.session.showSummary();
        }
        break;
    }
  }
}
