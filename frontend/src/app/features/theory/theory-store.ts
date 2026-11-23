import { computed, inject, linkedSignal, Service, signal } from '@angular/core';
import { Api } from '../../core/api';
import { LEVELS, Level, TopicSummary } from '../../core/models';

export interface TopicGroup {
  level: Level;
  topics: TopicSummary[];
}

/** State of the theory part: the topic list, the selected topic and its card. */
@Service()
export class TheoryStore {
  private readonly api = inject(Api);

  readonly topics = this.api.topics();

  /** The selected topic. The first topic is the default when the list loads. */
  readonly selectedId = linkedSignal<string | null>(() => this.topics.value()[0]?.id ?? null);

  readonly card = this.api.topic(this.selectedId);

  /** The section that the practice feedback refers to (RF-04). */
  readonly highlighted = signal<string | null>(null);

  readonly groups = computed<TopicGroup[]>(() =>
    LEVELS.map((level) => ({
      level,
      topics: this.topics.value().filter((t) => t.level === level),
    })).filter((g) => g.topics.length > 0),
  );

  select(id: string): void {
    this.selectedId.set(id);
    this.highlighted.set(null);
  }
}
