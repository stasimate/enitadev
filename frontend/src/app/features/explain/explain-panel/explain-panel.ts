import { Component, inject, Injector } from '@angular/core';
import { MarkdownPipe } from '../../../shared/pipes/markdown-pipe';
import { Speakable } from '../../../shared/directives/speakable';
import { scrollToSection } from '../../theory/scroll-to-section';
import { TheoryStore } from '../../theory/theory-store';
import { ExplainStore } from '../explain-store';

/** The "Spiegami meglio" button and the explanation that the Tutor writes. */
@Component({
  selector: 'en-explain-panel',
  imports: [MarkdownPipe, Speakable],
  host: { class: 'flex flex-col gap-3' },
  template: `
    <button
      type="button"
      class="self-start border-2 border-ink px-4 py-2 font-bold uppercase shadow-brutal-sm disabled:opacity-60"
      [disabled]="!theory.selectedId() || explain.status() === 'loading'"
      (click)="explain.explain()"
    >
      [ Spiegami meglio ]
    </button>

    @if (explain.status() === 'loading') {
      <p aria-live="polite">Il Tutor sta preparando la spiegazione<span class="cursor-blink">_</span></p>
    }

    @if (explain.error(); as message) {
      <div
        role="alert"
        class="flex flex-wrap items-center justify-between gap-3 border-2 border-err p-4 text-err"
      >
        <p>[ ERRORE ] {{ message }}</p>
        @if (explain.retryable()) {
          <button
            type="button"
            class="border-2 border-err px-3 py-1 font-bold uppercase shadow-brutal-sm"
            (click)="explain.explain()"
          >
            [ Riprova ]
          </button>
        }
      </div>
    }

    @if (explain.explanation(); as text) {
      <section aria-label="Spiegazione del Tutor" class="border-2 border-ink p-4 shadow-brutal">
        <h4 class="mb-2 text-sm font-bold uppercase">// Spiegazione</h4>
        <div class="md" [enSpeakable]="text" [innerHTML]="text | markdown"></div>
        @if (explain.sources().length) {
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <span class="text-sm font-bold uppercase">Fonti:</span>
            @for (source of explain.sources(); track source.rule_ref) {
              @if (isCurrentTopic(source.rule_ref)) {
                <button
                  type="button"
                  class="border-2 border-ink px-2 py-1 text-sm font-bold shadow-brutal-sm"
                  (click)="showSource(source.rule_ref)"
                >
                  [ {{ source.title }} ]
                </button>
              } @else {
                <span class="border-2 border-ink px-2 py-1 text-sm">[ {{ source.title }} ]</span>
              }
            }
          </div>
        }
      </section>
    }
  `,
})
export class ExplainPanel {
  protected readonly explain = inject(ExplainStore);
  protected readonly theory = inject(TheoryStore);
  private readonly injector = inject(Injector);

  protected isCurrentTopic(ruleRef: string): boolean {
    return ruleRef.split('#')[0] === this.theory.selectedId();
  }

  /** Highlight the section of the source and scroll to it. */
  protected showSource(ruleRef: string): void {
    const slug = ruleRef.split('#')[1];
    if (!slug) return;
    this.theory.highlighted.set(slug);
    scrollToSection(slug, this.injector);
  }
}
