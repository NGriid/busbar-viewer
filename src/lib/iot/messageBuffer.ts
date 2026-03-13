/**
 * Rolling in-memory message buffer.
 * Keeps the latest N messages, discarding oldest on overflow.
 */

import type { RawIoTMessage } from '../../types/iot';

const DEFAULT_CAPACITY = 100;

export class MessageBuffer {
    private messages: RawIoTMessage[] = [];
    private totalCount = 0;
    private readonly capacity: number;

    constructor(capacity = DEFAULT_CAPACITY) {
        this.capacity = capacity;
    }

    /** Add a message. Drops oldest if at capacity. */
    push(message: RawIoTMessage): void {
        this.totalCount++;
        this.messages.push(message);
        if (this.messages.length > this.capacity) {
            this.messages.shift();
        }
    }

    /** Get all buffered messages (newest last). */
    getAll(): readonly RawIoTMessage[] {
        return this.messages;
    }

    /** Total messages received since last clear (may exceed buffer size). */
    getTotalCount(): number {
        return this.totalCount;
    }

    /** Timestamp of the most recent message, or null. */
    getLastTimestamp(): string | null {
        const last = this.messages[this.messages.length - 1];
        return last?.receivedAt ?? null;
    }

    /** Get the latest message, or null. */
    getLatest(): RawIoTMessage | null {
        return this.messages[this.messages.length - 1] ?? null;
    }

    /** Clear all messages and reset the counter. */
    clear(): void {
        this.messages = [];
        this.totalCount = 0;
    }
}
