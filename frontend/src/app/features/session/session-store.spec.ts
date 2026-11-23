import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Exercise, Feedback, Verdict } from '../../core/models';
import { PracticeStore } from '../practice/practice-store';
import { TheoryStore } from '../theory/theory-store';
import { SessionStore } from './session-store';

const exercise = (n: number): Exercise => ({
  id: `ex${n}`,
  topic_id: 'past-simple',
  type: 'fill_blank',
  instruction: 'i',
  prompt: 'p',
  options: [],
});
const feedback = (verdict: Verdict, rule = 'past-simple#esempi'): Feedback => ({
  verdict,
  score: 0,
  correct_answer: 'x',
  explanation: 'e',
  rule_ref: rule,
});

describe('SessionStore', () => {
  let session: SessionStore;
  let practice: PracticeStore;
  let theory: TheoryStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    theory = TestBed.inject(TheoryStore);
    practice = TestBed.inject(PracticeStore);
    session = TestBed.inject(SessionStore);
    theory.selectedId.set('past-simple');
    TestBed.tick();
    http.match(() => true);
  });

  /** Create one exercise and answer it. */
  function play(n: number, fb: Feedback): void {
    if (n === 1) session.start();
    else session.next();
    http.expectOne('/api/exercises').flush(exercise(n));
    practice.submit('a');
    http.expectOne(`/api/exercises/ex${n}/answer`).flush(fb);
    TestBed.tick();
  }

  it('counts 10 exercises, collects the wrong ones and ends', () => {
    for (let n = 1; n <= 10; n++) {
      play(
        n,
        n <= 7 ? feedback('correct') : feedback(n === 8 ? 'partial' : 'wrong', `past-simple#r${n}`),
      );
      expect(session.position()).toBe(n);
      expect(session.finished()).toBe(n === 10);
    }
    expect(session.correct()).toBe(7);
    expect(session.wrong().map((r) => r.feedback.rule_ref)).toEqual([
      'past-simple#r8',
      'past-simple#r9',
      'past-simple#r10',
    ]);
    expect(session.canContinue()).toBe(false);
    expect(session.summaryOpen()).toBe(false);
    session.showSummary();
    expect(session.summaryOpen()).toBe(true);
  });

  it('does not count a retry after a temporary error', () => {
    session.start();
    http.expectOne('/api/exercises').flush({}, { status: 504, statusText: 'Timeout' });
    practice.retry();
    http.expectOne('/api/exercises').flush(exercise(1));
    TestBed.tick();
    expect(session.results().length).toBe(0);
    expect(session.position()).toBe(1);
  });

  it('resets when the topic changes', async () => {
    play(1, feedback('correct'));
    expect(session.results().length).toBe(1);
    theory.select('other');
    await new Promise((r) => setTimeout(r));
    TestBed.tick();
    http.match(() => true);
    expect(session.active()).toBe(false);
    expect(session.results()).toEqual([]);
  });
});
