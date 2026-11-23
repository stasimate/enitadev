import { afterRenderEffect, Directive, ElementRef, inject, input } from '@angular/core';

const BUTTON_CLASS =
  'ml-1 border border-ink px-1 align-middle text-xs font-bold hover:bg-ink hover:text-paper';

/** True when the browser can speak text. */
function canSpeak(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/**
 * Adds a play button after each inline `code` element of the rendered markdown.
 * The button speaks the English text. Crossed out text (`del`) is a wrong form: skip it.
 * Set `enSpeakable` to the markdown source. The buttons are made again when it changes.
 */
@Directive({
  selector: '[enSpeakable]',
  host: { '(click)': 'onClick($event)' },
})
export class Speakable {
  readonly enSpeakable = input<string | null | undefined>();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

  constructor() {
    afterRenderEffect(() => {
      this.enSpeakable();
      if (canSpeak()) this.decorate();
    });
  }

  private decorate(): void {
    for (const code of Array.from(this.host.querySelectorAll('code'))) {
      const text = code.textContent?.trim();
      if (!text || code.closest('del, pre') || code.nextElementSibling?.hasAttribute('data-speak'))
        continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = BUTTON_CLASS;
      button.textContent = '[▶]';
      button.setAttribute('aria-label', `Ascolta: ${text}`);
      button.setAttribute('data-speak', text);
      code.after(button);
    }
  }

  protected onClick(event: Event): void {
    const button = (event.target as HTMLElement).closest('button[data-speak]');
    const text = button?.getAttribute('data-speak');
    if (!text || !canSpeak()) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-GB';
    utterance.rate = 0.9;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }
}
