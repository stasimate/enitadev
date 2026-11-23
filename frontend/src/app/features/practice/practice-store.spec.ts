import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { AttemptFeedback, Exercise } from '../../core/models';
import { TheoryStore } from '../theory/theory-store';
import { PracticeStore } from './practice-store';

const EXERCISE: Exercise = {
  id: 'ex1',
  topic_id: 'past-simple',
  type: 'fill_blank',
  instruction: 'Completa',
  prompt: 'I ___ yesterday.',
  options: [],
  context: '',
};
const SOLUTION = { model_answer: 'worked', corrected: null, explanation: 'Usa il past simple.' };
const FEEDBACK: AttemptFeedback = {
  attempt: 1,
  verdict: 'wrong',
  score: 0,
  feedback: 'Manca il past simple.',
  hint: 'Pensa a ieri.',
  errors: ['verbo al presente'],
  rule_ref: 'past-simple#esempi',
  done: false,
  solution: null,
};
const DONE: AttemptFeedback = {
  ...FEEDBACK,
  attempt: 2,
  verdict: 'correct',
  score: 1,
  hint: null,
  errors: [],
  done: true,
  solution: SOLUTION,
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
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    theory = TestBed.inject(TheoryStore);
    store = TestBed.inject(PracticeStore);
    theory.selectedId.set('past-simple');
    TestBed.tick();
    // The theory resources are not under test.
    http.match(() => true);
  });

  function open(): void {
    store.newExercise('past-simple');
    http.expectOne('/api/exercises').flush(EXERCISE);
  }

  it('creates an exercise and keeps it open after a feedback that is not done', () => {
    store.newExercise('past-simple');
    expect(store.status()).toBe('loading');
    const create = http.expectOne('/api/exercises');
    expect(create.request.body).toEqual({ topic_id: 'past-simple', type: undefined });
    create.flush(EXERCISE);
    expect(store.status()).toBe('answering');

    store.submit('work');
    expect(store.status()).toBe('checking');
    const answer = http.expectOne('/api/exercises/ex1/answer');
    expect(answer.request.body).toEqual({ answer: 'work' });
    answer.flush(FEEDBACK);
    expect(store.attempts()).toEqual([{ answer: 'work', feedback: FEEDBACK }]);
    expect(store.status()).toBe('answering');
    expect(store.canShowSolution()).toBe(true);

    store.showRule();
    expect(theory.highlighted()).toBe('esempi');
  });

  it('keeps all attempts and closes the exercise on a done feedback', () => {
    open();
    store.submit('work');
    http.expectOne('/api/exercises/ex1/answer').flush(FEEDBACK);
    store.submit('worked');
    http.expectOne('/api/exercises/ex1/answer').flush(DONE);
    expect(store.attempts().map((a) => a.answer)).toEqual(['work', 'worked']);
    expect(store.status()).toBe('done');
    expect(store.solution()).toEqual(SOLUTION);
    expect(store.outcome()).toEqual({
      attempts: 2,
      verdict: 'correct',
      ruleRef: 'past-simple#esempi',
    });
    // A closed exercise accepts no answer.
    store.submit('again');
    http.expectNone('/api/exercises/ex1/answer');
  });

  it('closes the exercise and stores the solution from the solution endpoint', () => {
    open();
    store.submit('work');
    http.expectOne('/api/exercises/ex1/answer').flush(FEEDBACK);
    store.showSolution();
    const req = http.expectOne('/api/exercises/ex1/solution');
    expect(req.request.method).toBe('POST');
    req.flush(SOLUTION);
    expect(store.solution()).toEqual(SOLUTION);
    expect(store.status()).toBe('done');
    expect(store.outcome().verdict).toBe('wrong');
  });

  it('closes the exercise on a 409', () => {
    open();
    store.submit('x');
    http
      .expectOne('/api/exercises/ex1/answer')
      .flush({ detail: 'closed' }, { status: 409, statusText: 'Conflict' });
    expect(store.status()).toBe('done');
    expect(store.error()).toBe('Questo esercizio è già chiuso.');
    expect(store.retryable()).toBe(false);
  });

  it('does not highlight a rule of another topic', () => {
    store.showRule('other#regola');
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

  it('prefetches the exercises when the topic changes', async () => {
    theory.select('other');
    await settle();
    const prefetch = http.expectOne('/api/topics/other/prefetch');
    expect(prefetch.request.method).toBe('POST');
    prefetch.flush(null, { status: 202, statusText: 'Accepted' });
    http.match(() => true);
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
