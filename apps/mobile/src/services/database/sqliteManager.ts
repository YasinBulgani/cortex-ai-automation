import SQLite from 'react-native-sqlite-storage';

let db: SQLite.Database | null = null;

export const initDatabase = async (): Promise<void> => {
  try {
    db = await SQLite.openDatabase({
      name: 'neurex.db',
      location: 'default',
    });

    await createTables();
    console.log('SQLite database initialized');
  } catch (error) {
    console.error('Database initialization error:', error);
    throw error;
  }
};

const createTables = async (): Promise<void> => {
  if (!db) return;

  const tables = [
    // Test Cases table
    `CREATE TABLE IF NOT EXISTS test_cases (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      status TEXT DEFAULT 'draft',
      tags TEXT,
      steps TEXT,
      created_at TEXT,
      updated_at TEXT,
      synced BOOLEAN DEFAULT 0
    );`,

    // Execution Results table
    `CREATE TABLE IF NOT EXISTS execution_results (
      id TEXT PRIMARY KEY,
      test_case_id TEXT NOT NULL,
      status TEXT DEFAULT 'pending',
      duration_seconds INTEGER,
      started_at TEXT,
      completed_at TEXT,
      error_message TEXT,
      screenshots TEXT,
      logs TEXT,
      synced BOOLEAN DEFAULT 0,
      FOREIGN KEY (test_case_id) REFERENCES test_cases(id)
    );`,

    // Defects table
    `CREATE TABLE IF NOT EXISTS defects (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      test_case_id TEXT,
      title TEXT NOT NULL,
      description TEXT,
      status TEXT DEFAULT 'new',
      severity TEXT,
      assignee_id TEXT,
      created_at TEXT,
      updated_at TEXT,
      synced BOOLEAN DEFAULT 0
    );`,

    // Defect Comments table
    `CREATE TABLE IF NOT EXISTS defect_comments (
      id TEXT PRIMARY KEY,
      defect_id TEXT NOT NULL,
      author_id TEXT,
      text TEXT,
      created_at TEXT,
      synced BOOLEAN DEFAULT 0,
      FOREIGN KEY (defect_id) REFERENCES defects(id)
    );`,

    // Sync Queue for offline changes
    `CREATE TABLE IF NOT EXISTS sync_queue (
      id TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      action TEXT,
      data TEXT,
      created_at TEXT,
      synced BOOLEAN DEFAULT 0
    );`,
  ];

  for (const sql of tables) {
    try {
      await db.executeSql(sql);
    } catch (error) {
      console.warn('Table creation warning:', error);
    }
  }
};

export const getDatabase = (): SQLite.Database | null => db;

export const insertTestCase = async (testCase: any): Promise<void> => {
  if (!db) throw new Error('Database not initialized');

  const sql = `INSERT OR REPLACE INTO test_cases (
    id, project_id, title, description, status, tags, steps, created_at, updated_at
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);`;

  const params = [
    testCase.id,
    testCase.project_id,
    testCase.title,
    testCase.description,
    testCase.status,
    JSON.stringify(testCase.tags || []),
    JSON.stringify(testCase.steps || []),
    testCase.created_at,
    testCase.updated_at,
  ];

  await db.executeSql(sql, params);
};

export const getTestCases = async (projectId: string): Promise<any[]> => {
  if (!db) throw new Error('Database not initialized');

  const sql = 'SELECT * FROM test_cases WHERE project_id = ? ORDER BY updated_at DESC;';
  const result = await db.executeSql(sql, [projectId]);

  const testCases: any[] = [];
  for (let i = 0; i < result.rows.length; i++) {
    const row = result.rows.item(i);
    testCases.push({
      ...row,
      tags: JSON.parse(row.tags || '[]'),
      steps: JSON.parse(row.steps || '[]'),
    });
  }

  return testCases;
};

export const insertExecutionResult = async (result: any): Promise<void> => {
  if (!db) throw new Error('Database not initialized');

  const sql = `INSERT OR REPLACE INTO execution_results (
    id, test_case_id, status, duration_seconds, started_at, completed_at, error_message, screenshots, logs
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);`;

  const params = [
    result.id,
    result.test_case_id,
    result.status,
    result.duration_seconds,
    result.started_at,
    result.completed_at,
    result.error_message,
    JSON.stringify(result.screenshots || []),
    JSON.stringify(result.logs || []),
  ];

  await db.executeSql(sql, params);
};

export const deleteTestCase = async (id: string): Promise<void> => {
  if (!db) throw new Error('Database not initialized');

  await db.executeSql('DELETE FROM test_cases WHERE id = ?;', [id]);
};

export const clearDatabase = async (): Promise<void> => {
  if (!db) throw new Error('Database not initialized');

  const tables = ['test_cases', 'execution_results', 'defects', 'defect_comments', 'sync_queue'];

  for (const table of tables) {
    try {
      await db.executeSql(`DELETE FROM ${table};`);
    } catch (error) {
      console.warn(`Failed to clear table ${table}:`, error);
    }
  }
};
