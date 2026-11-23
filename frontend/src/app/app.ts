import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

/** The application shell: the header with the navigation and the routed page. */
@Component({
  selector: 'en-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="flex min-h-dvh flex-col">
      <header
        class="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink px-4 py-3"
      >
        <h1 class="text-xl font-bold tracking-tight">
          ENITA<span class="cursor-blink text-accent">_</span>
        </h1>
        <nav class="flex gap-2" aria-label="Pagine">
          <a
            routerLink="/"
            routerLinkActive="bg-ink text-paper"
            ariaCurrentWhenActive="page"
            [routerLinkActiveOptions]="{ exact: true }"
            class="border-2 border-ink px-3 py-1 font-bold uppercase shadow-brutal-sm"
          >
            [ Studia ]
          </a>
          <a
            routerLink="/progressi"
            routerLinkActive="bg-ink text-paper"
            ariaCurrentWhenActive="page"
            class="border-2 border-ink px-3 py-1 font-bold uppercase shadow-brutal-sm"
          >
            [ Progressi ]
          </a>
        </nav>
      </header>
      <router-outlet />
    </div>
  `,
})
export class App {}
