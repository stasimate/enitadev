import { afterNextRender, Injector } from '@angular/core';

/**
 * Scroll to a theory section after the next render.
 * On large screens the theory pane scrolls by itself. The browser scrolls that pane.
 */
export function scrollToSection(slug: string | null, injector: Injector): void {
  afterNextRender(
    () => {
      if (!slug) return;
      document
        .getElementById(`sec-${slug}`)
        ?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    },
    { injector },
  );
}
