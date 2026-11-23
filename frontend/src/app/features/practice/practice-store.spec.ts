import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Exercise, Feedback } from '../../core/models';
import { TheoryStore } from '../theory/theory-store';
import { PracticeStore } from './practice-store';

const EXERCISE: Exercise = {
  id: 'ex1',
  topic_id: 'past-simple',
  type: 'fill_blank',
  instruction: 'Completa',
  prompt: 'I ___ yesterday.',
  options: [],
};
const FEEDBACK: Feedback = {
  verdict: 'wrong',
  score: 0,
  correct_answer: 'worked',
  explanation: 'Usa il past simple.',
  rule_ref: 'past-simple#esempi',
};

async function settle(): Promise<void> {
  await new Promise((r) => setTimeout(r));
  TestBed.tick();
}

describe('PracticeStore', () => {
  let store: PracticeStore;
  let theory: TheoryStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    theory = TestBed.inject(TheoryStore);
    store = TestBed.inject(PracticeStore);
    theory.selectedId.set('past-simple');
    TestBed.tick();
    // The theory resources are not under test.
    http.match(() => true);
  });

  it('creates an exercise, checks the answer and highlights the rule', () => {
    store.newExercise('past-simple');
    expect(store.status()).toBe('loading');
    const create = http.expectOne('/api/exercises');
    expect(create.request.body).toEqual({ topic_id: 'past-simple', type: undefined });
    create.flush(EXERCISE);
    expect(store.exercise()).toEqual(EXERCISE);
    expect(store.status()).toBe('answering');

    store.submit('worked');
    expect(store.status()).toBe('checking');
    const answer = http.expectOne('/api/exercises/ex1/answer');
    expect(answer.request.body).toEqual({ answer: 'worked' });
    answer.flush(FEEDBACK);
    expect(store.feedback()).toEqual(FEEDBACK);
    expect(store.status()).toBe('feedback');

    store.showRule();
    expect(theory.highlighted()).toBe('esempi');
  });

  it('does not highlight a rule of another topic', () => {
    store.feedback.set({ ...FEEDBACK, rule_ref: 'other#regola' });
    store.showRule();
    expect(theory.highlighted()).toBeNull();
  });

  it('lets the student retry only a temporary error', () => {
    store.newExercise('past-simple');
    http.expectOne('/api/exercises').flush({ detail: 'x' }, { status: 504, statusText: 'Timeout' });
    expect(store.status()).toBe('error');
    expect(store.error()).toBe('Il Tutor ci mette troppo tempo.');
    expect(store.retryable()).toBe(true);

    store.retry();
    const again = http.expectOne('/api/exercises');
    expect(again.request.body.topic_id).toBe('past-simple');
    again.flush({ detail: 'key' }, { status: 503, statusText: 'Unavailable' });
    expect(store.retryable()).toBe(false);
  });

  it('shows the 422 detail and lets the student answer again', () => {
    store.newExercise('past-simple');
    http.expectOne('/api/exercises').flush(EXERCISE);
    store.submit('x');
    http
      .expectOne('/api/exercises/ex1/answer')
      .flush({ detail: 'Risposta troppo lunga.' }, { status: 422, statusText: 'Unprocessable' });
    expect(store.error()).toBe('Risposta troppo lunga.');
    expect(store.status()).toBe('answering');
  });

  it('maps other errors to the backend message', () => {
    store.newExercise('past-simple');
    http.expectOne('/api/exercises').error(new ProgressEvent('error'));
    expect(store.error()).toBe('Il backend non risponde.');
  });

  it('resets when the theory topic changes', async () => {
    store.newExercise('past-simple');
    http.expectOne('/api/exercises').flush(EXERCISE);
    theory.select('other');
    await settle();
    http.match(() => true);
    expect(store.exercise()).toBeNull();
    expect(store.status()).toBe('idle');
  });
});
