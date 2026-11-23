import { httpResource } from '@angular/common/http';
import { Service } from '@angular/core';
import { TopicCard, TopicSummary } from './models';

/**
 * The only access point to the backend REST API.
 * Call the methods in an injection context (for example, a field initializer).
 */
@Service()
export class Api {
  topics() {
    return httpResource<TopicSummary[]>(() => '/api/topics', { defaultValue: [] });
  }

  topic(id: () => string | null) {
    return httpResource<TopicCard>(() => {
      const value = id();
      return value ? `/api/topics/${encodeURIComponent(value)}` : undefined;
    });
  }
}
