import { Component, computed, inject, output } from '@angular/core';
import { TheoryStore } from '../../theory/theory-store';
import { AnswerForm } from '../answer-form/answer-form';
import { ExerciseView } from '../exercise-view/exercise-view';
import { FeedbackView } from '../feedback-view/feedback-view';
import { SessionStore } from '../../session/session-store';
import { SessionSummary } from '../../session/session-summary/session-summary';
import { PracticeShortcuts } from '../practice-shortcuts';
import { PracticeStore } from '../practice-store';
import { SolutionView } from '../solution-view/solution-view';

/** The practice part: it arranges the exercise, the thread of attempts and the solution. */
@Component({
  selector: 'en-practice-panel',
  host: { '(document:keydown)': 'shortcuts.handle($event)' },
  imports: [ExerciseView, AnswerForm, FeedbackView, SolutionView, SessionSummary],
  template: `
    <div class="flex flex-col gap-4 border-2 border-ink p-4 shadow-brutal">
      @if (!theory.selectedId()) {
        <p>Scegli un argomento per iniziare.</p>
      }
      @if (session.summaryOpen()) {
        <en-session-summary
          [correct]="session.correct()"
          [total]="session.size"
          [results]="session.results()"
          (showRule)="onShowRule($event)"
          (restart)="session.start()"
          (closed)="session.close()"
        />
      } @else {
        @if (session.active()) {
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="font-bold uppercase" aria-live="polite">
              Esercizio {{ session.position() }}/{{ session.size }} · Corrette
              {{ session.correct() }}
            </p>
            <button
              type="button"
              class="border-2 border-ink px-3 py-1 font-bold uppercase shadow-brutal-sm"
              (click)="session.close()"
            >
              [ Chiudi ]
            </button>
          </div>
        } @else {
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="self-start border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
              [disabled]="!canStart()"
              (click)="start()"
            >
              [ Nuovo esercizio ]
            </button>
            <button
              type="button"
              class="border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
              [disabled]="!canStart()"
              (click)="session.start()"
            >
              [ Inizia sessione ({{ session.size }}) ]
            </button>
          </div>
        }

        @if (practice.status() === 'loading') {
          <p aria-live="polite">
            Il Tutor sta scrivendo l'esercizio<span class="cursor-blink">_</span>
          </p>
        }

        @if (practice.exercise(); as exercise) {
          <en-exercise-view [exercise]="exercise" />
          @for (attempt of practice.attempts(); track $index) {
            <en-feedback-view [attempt]="attempt" />
          }
          <!-- The slot changes with each attempt, so each attempt gets a new empty input. -->
          @for (slot of openSlots(); track slot) {
            <div class="flex flex-col gap-2">
              <h3 class="text-sm font-bold uppercase">// Tentativo {{ slot + 1 }}</h3>
              <en-answer-form
                [exercise]="exercise"
                [disabled]="practice.status() === 'checking'"
                (answered)="practice.submit($event)"
              />
            </div>
          }
          @if (practice.status() === 'checking') {
            <p aria-live="polite">Il Tutor sta correggendo<span class="cursor-blink">_</span></p>
          }
          @if (practice.canShowSolution()) {
            <button
              type="button"
              class="self-start border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm"
              (click)="practice.showSolution()"
            >
              [ Mostra soluzione ]
            </button>
          }
          @if (practice.solution(); as solution) {
            <en-solution-view
              [solution]="solution"
              [ruleRef]="practice.outcome().ruleRef"
              (showRule)="onShowRule()"
            />
          }
        }

        @if (session.finished() && practice.status() === 'done') {
          <button
            type="button"
            class="self-start border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm"
            (click)="session.showSummary()"
          >
            [ Risultato ]
          </button>
        }
        @if (session.canContinue()) {
          <button
            type="button"
            class="self-start border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm"
            (click)="session.next()"
          >
            [ Prossimo ]
          </button>
        }
      }

      <p class="text-xs">TASTI: 1–4 · N · P</p>

      @if (practice.error(); as message) {
        <div
          role="alert"
          class="flex flex-wrap items-center justify-between gap-3 border-2 border-err p-4 text-err"
        >
          <p>[ ERRORE ] {{ message }}</p>
          @if (practice.retryable()) {
            <button
              type="button"
              class="border-2 border-err px-3 py-1 font-bold uppercase shadow-brutal-sm"
              (click)="practice.retry()"
            >
              [ Riprova ]
            </button>
          }
        </div>
      }
    </div>
  `,
})
export class PracticePanel {
  protected readonly theory = inject(TheoryStore);
  protected readonly practice = inject(PracticeStore);
  protected readonly session = inject(SessionStore);
  protected readonly shortcuts = inject(PracticeShortcuts);

  /** Sent after the theory section is highlighted. The shell then shows it. */
  readonly ruleShown = output<void>();

  /** One slot while the exercise is open, none when it is closed. The slot is the attempt index. */
  protected readonly openSlots = computed(() =>
    ['answering', 'checking'].includes(this.practice.status()) ? [this.practice.attempts().length] : [],
  );

  protected readonly canStart = computed(
    () => !!this.theory.selectedId() && this.practice.status() !== 'loading',
  );

  protected start(): void {
    const id = this.theory.selectedId();
    if (id) this.practice.newExercise(id);
  }

  protected onShowRule(ruleRef?: string): void {
    this.practice.showRule(ruleRef);
    this.ruleShown.emit();
  }
}
