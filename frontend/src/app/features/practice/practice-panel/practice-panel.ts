import { Component, computed, inject, output } from '@angular/core';
import { TheoryStore } from '../../theory/theory-store';
import { AnswerForm } from '../answer-form/answer-form';
import { ExerciseView } from '../exercise-view/exercise-view';
import { FeedbackView } from '../feedback-view/feedback-view';
import { PracticeStore } from '../practice-store';

/** The practice part: it arranges the exercise, the answer form and the feedback. */
@Component({
  selector: 'en-practice-panel',
  imports: [ExerciseView, AnswerForm, FeedbackView],
  template: `
    <div class="flex flex-col gap-4 border-2 border-ink p-4 shadow-brutal">
      @if (!theory.selectedId()) {
        <p>Scegli un argomento per iniziare.</p>
      }
      <button
        type="button"
        class="self-start border-2 border-ink bg-accent px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
        [disabled]="!canStart()"
        (click)="start()"
      >
        [ Nuovo esercizio ]
      </button>

      @if (practice.status() === 'loading') {
        <p aria-live="polite">Il Tutor sta scrivendo l'esercizio<span class="cursor-blink">_</span></p>
      }

      @if (practice.exercise(); as exercise) {
        <en-exercise-view [exercise]="exercise" />
        @if (practice.status() !== 'feedback') {
          <en-answer-form
            [exercise]="exercise"
            [disabled]="practice.status() === 'checking'"
            (answered)="practice.submit($event)"
          />
        }
        @if (practice.status() === 'checking') {
          <p aria-live="polite">Il Tutor sta correggendo<span class="cursor-blink">_</span></p>
        }
      }

      <en-feedback-view [feedback]="practice.feedback()" (showRule)="onShowRule()" />

      @if (practice.error(); as message) {
        <p role="alert" class="border-2 border-err p-4 text-err">[ ERRORE ] {{ message }}</p>
      }
    </div>
  `,
})
export class PracticePanel {
  protected readonly theory = inject(TheoryStore);
  protected readonly practice = inject(PracticeStore);

  /** Sent after the theory section is highlighted. The shell then shows it. */
  readonly ruleShown = output<void>();

  protected readonly canStart = computed(
    () => !!this.theory.selectedId() && this.practice.status() !== 'loading',
  );

  protected start(): void {
    const id = this.theory.selectedId();
    if (id) this.practice.newExercise(id);
  }

  protected onShowRule(): void {
    this.practice.showRule();
    this.ruleShown.emit();
  }
}
