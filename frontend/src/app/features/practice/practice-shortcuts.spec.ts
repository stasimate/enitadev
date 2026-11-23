import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { SessionStore } from '../session/session-store';
import { TheoryStore } from '../theory/theory-store';
import { PracticeShortcuts, shortcutFor } from './practice-shortcuts';
import { PracticeStore } from './practice-store';

function press(key: string, target: EventTarget | null = null, mods = {}): KeyboardEvent {
  return { key, target, ctrlKey: false, metaKey: false, altKey: false, ...mods } as KeyboardEvent;
}

describe('shortcutFor', () => {
  it('maps 1-4, N and P and ignores other keys', () => {
    expect(shortcutFor(press('1'))).toEqual({ kind: 'choose', index: 0 });
    expect(shortcutFor(press('4'))).toEqual({ kind: 'choose', index: 3 });
    expect(shortcutFor(press('5'))).toBeNull();
    expect(shortcutFor(press('n'))).toEqual({ kind: 'new' });
    expect(shortcutFor(press('N'))).toEqual({ kind: 'new' });
    expect(shortcutFor(press('p'))).toEqual({ kind: 'next' });
    expect(shortcutFor(press('x'))).toBeNull();
  });

  it('ignores keys typed in fields and keys with modifiers', () => {
    expect(shortcutFor(press('n', document.createElement('input')))).toBeNull();
    expect(shortcutFor(press('1', document.createElement('textarea')))).toBeNull();
    expect(shortcutFor(press('p', document.createElement('select')))).toBeNull();
    expect(shortcutFor(press('n', null, { metaKey: true }))).toBeNull();
    expect(shortcutFor(press('n', null, { ctrlKey: true }))).toBeNull();
    expect(shortcutFor(press('n', document.createElement('button')))).toEqual({ kind: 'new' });
  });
});

describe('PracticeShortcuts', () => {
  const practice = {
    exercise: signal<unknown>({ type: 'multiple_choice', options: ['a', 'b'] }),
    status: signal('answering'),
    submit: vi.fn(),
    newExercise: vi.fn(),
  };
  const session = {
    active: signal(false),
    finished: signal(false),
    canContinue: signal(false),
    next: vi.fn(),
    showSummary: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        { provide: PracticeStore, useValue: practice },
        { provide: SessionStore, useValue: session },
        { provide: TheoryStore, useValue: { selectedId: signal('t1') } },
      ],
    });
  });

  it('answers a multiple choice with the number keys', () => {
    const shortcuts = TestBed.inject(PracticeShortcuts);
    shortcuts.handle(press('2'));
    expect(practice.submit).toHaveBeenCalledWith('b');
    shortcuts.handle(press('4'));
    expect(practice.submit).toHaveBeenCalledTimes(1);
  });

  it('starts a new exercise with N and moves on with P', () => {
    const shortcuts = TestBed.inject(PracticeShortcuts);
    shortcuts.handle(press('n'));
    expect(practice.newExercise).toHaveBeenCalledWith('t1');
    session.canContinue.set(true);
    shortcuts.handle(press('p'));
    expect(session.next).toHaveBeenCalled();
    session.canContinue.set(false);
    session.finished.set(true);
    practice.status.set('done');
    shortcuts.handle(press('p'));
    expect(session.showSummary).toHaveBeenCalled();
  });
});
