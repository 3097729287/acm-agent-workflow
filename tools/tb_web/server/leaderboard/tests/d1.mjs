// The same production queries execute against real SQLite, not hand-written SQL stubs.
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';

export class D1Fixture {
  constructor(path = ':memory:') {
    this.database = new DatabaseSync(path);
    this.database.exec('PRAGMA foreign_keys=ON');
    const exists = this.database.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").get();
    if (!exists) this.database.exec(readFileSync(new URL('../migrations/0001_schema.sql', import.meta.url), 'utf8'));
  }
  prepare(query) { return new Statement(this.database, query); }
  async batch(statements) {
    this.database.exec('BEGIN IMMEDIATE');
    try {
      const results = [];
      // A single synchronous SQLite transaction also models parallel HTTP batches.
      for (const statement of statements) {
        const row = this.database.prepare(statement.query).run(...statement.values);
        results.push({ success: true, meta: { changes: row.changes } });
      }
      this.database.exec('COMMIT'); return results;
    } catch (error) { this.database.exec('ROLLBACK'); throw error; }
  }
  close() { this.database.close(); }
}

class Statement {
  constructor(database, query, values = []) { this.database = database; this.query = query; this.values = values; }
  bind(...values) { return new Statement(this.database, this.query, values); }
  async first() { return this.database.prepare(this.query).get(...this.values) || null; }
  async all() { return { success: true, results: this.database.prepare(this.query).all(...this.values) }; }
  async run() { const result = this.database.prepare(this.query).run(...this.values); return { success: true, meta: { changes: result.changes } }; }
}
