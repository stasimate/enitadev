import { computed, inject, Service } from '@angular/core';
import { Router } from '@angular/router';
import { Api } from '../../core/api';
import { TheoryStore } from '../theory/theory-store';
import { buildErrors, buildRows, buildStrip } from './progress-model';

/** State of the progress page. Provide it in the page, so each visit loads fresh data. */
@Service({ autoProvided: false })
export class ProgressStore {
  private readonly api = inject(Api);
  private readonly theory = inject(TheoryStore);
  private readonly router = inject(Router);

  readonly profile = this.api.progress();

  readonly rows = computed(() =>
    buildRows(this.theory.topics.value(), this.profile.value()?.topics ?? []),
  );
  readonly strip = computed(() => buildStrip(this.profile.value()?.active_days ?? [], new Date()));
  readonly errors = computed(() =>
    buildErrors(this.profile.value()?.frequent_errors ?? {}, this.theory.topics.value()),
  );
  readonly streak = computed(() => this.profile.value()?.streak_days ?? 0);

  /** Go to the study page, select the topic and highlight the section. */
  openRule(ruleRef: string): void {
    const [topicId, slug] = ruleRef.split('#');
    if (!topicId) return;
    this.theory.select(topicId);
    if (slug) this.theory.highlighted.set(slug);
    void this.router.navigateByUrl('/');
  }
}
