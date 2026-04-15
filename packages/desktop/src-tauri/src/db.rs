use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobSummary {
    pub passed: bool,
    pub error_count: u32,
    pub warning_count: u32,
    pub advisory_count: u32,
}

/// Tokenised report URLs minted via `POST /api/v1/jobs/{job_id}/reports`.
/// Cached locally so links survive app restarts.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ShareLinks {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub html: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pdf: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub json: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub xml: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub annotated_pdf: Option<String>,
}

impl ShareLinks {
    pub fn is_empty(&self) -> bool {
        self.html.is_none()
            && self.pdf.is_none()
            && self.json.is_none()
            && self.xml.is_none()
            && self.annotated_pdf.is_none()
    }
}

/// Row states understood by the UI and the drainer.
pub mod status {
    /// Stabilized, not yet submitted. Drainer picks up when online.
    pub const QUEUED_OFFLINE: &str = "queued_offline";
    /// Submitted once, got a transient/transport error, backing off.
    pub const QUEUED_RETRY: &str = "queued_retry";
    /// Accepted by the engine, polling for result.
    pub const PROCESSING: &str = "processing";
    pub const PASSED: &str = "passed";
    pub const FAILED: &str = "failed";
    /// Terminal 4xx or local filesystem / config error.
    pub const ERROR: &str = "error";

    #[allow(dead_code)]
    pub fn is_queued(s: &str) -> bool {
        s == QUEUED_OFFLINE || s == QUEUED_RETRY
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobRecord {
    pub id: String,
    pub folder_id: String,
    pub file_name: String,
    pub file_path: String,
    pub status: String,
    pub job_id: Option<String>,
    pub summary: Option<JobSummary>,
    pub routed_to: Option<String>,
    pub submitted_at: String,
    pub completed_at: Option<String>,
    pub error_message: Option<String>,
    #[serde(default)]
    pub share_links: Option<ShareLinks>,

    /// Companion `.jdf` / `.xjdf` file captured at stabilization time.
    /// Stored so the drainer can attach it when retrying after an
    /// offline stretch — the watcher no longer has it in memory.
    #[serde(default)]
    pub jdf_path: Option<String>,

    /// Pre-submit grouping key: `{folder_id}-{window_start_epoch}` for
    /// rows that should submit as a single `/api/v1/batch/submit`. Null
    /// for folders without batch mode.
    #[serde(default)]
    pub batch_group: Option<String>,

    /// Engine-assigned batch id once `/api/v1/batch/submit` succeeds.
    /// Lets the UI group rows together in the Results table.
    #[serde(default)]
    pub batch_id: Option<String>,

    /// RFC3339 timestamp the drainer honours before picking this row up
    /// again. Supports exponential backoff without a sleeping task.
    #[serde(default)]
    pub next_retry_at: Option<String>,

    /// Backoff counter, reset on successful submit.
    #[serde(default)]
    pub retry_attempts: u32,
}

pub struct Database {
    conn: Mutex<Connection>,
}

impl Database {
    pub fn new() -> Result<Self, String> {
        let db_dir = dirs::data_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("lintpdf-desktop");
        std::fs::create_dir_all(&db_dir).ok();
        let db_path = db_dir.join("jobs.db");

        let conn = Connection::open(&db_path)
            .map_err(|e| format!("Failed to open database: {}", e))?;

        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                folder_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                job_id TEXT,
                summary_json TEXT,
                routed_to TEXT,
                submitted_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                share_links_json TEXT,
                jdf_path TEXT,
                batch_group TEXT,
                batch_id TEXT,
                next_retry_at TEXT,
                retry_attempts INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_submitted ON jobs(submitted_at DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_folder ON jobs(folder_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_batch_group ON jobs(batch_group);
            CREATE INDEX IF NOT EXISTS idx_jobs_batch_id ON jobs(batch_id);",
        )
        .map_err(|e| format!("Failed to create tables: {}", e))?;

        // Idempotent column migrations. Each guarded against re-run by
        // swallowing the "duplicate column name" SQLite error — same
        // pattern used for share_links_json in Phase 1.
        for col in [
            "share_links_json TEXT",
            "jdf_path TEXT",
            "batch_group TEXT",
            "batch_id TEXT",
            "next_retry_at TEXT",
            "retry_attempts INTEGER NOT NULL DEFAULT 0",
        ] {
            let stmt = format!("ALTER TABLE jobs ADD COLUMN {}", col);
            if let Err(e) = conn.execute(&stmt, []) {
                let msg = e.to_string();
                if !msg.contains("duplicate column name") {
                    log::warn!("Migration {} failed: {}", col, msg);
                }
            }
        }

        Ok(Self {
            conn: Mutex::new(conn),
        })
    }

    pub fn insert_job(&self, job: &JobRecord) -> Result<(), String> {
        let conn = self.conn.lock().unwrap();
        let summary_json = job
            .summary
            .as_ref()
            .map(|s| serde_json::to_string(s).unwrap_or_default());
        let share_links_json = job
            .share_links
            .as_ref()
            .filter(|s| !s.is_empty())
            .map(|s| serde_json::to_string(s).unwrap_or_default());

        conn.execute(
            "INSERT OR REPLACE INTO jobs (
                id, folder_id, file_name, file_path, status, job_id,
                summary_json, routed_to, submitted_at, completed_at,
                error_message, share_links_json, jdf_path,
                batch_group, batch_id, next_retry_at, retry_attempts
             ) VALUES (
                ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10,
                ?11, ?12, ?13, ?14, ?15, ?16, ?17
             )",
            params![
                job.id,
                job.folder_id,
                job.file_name,
                job.file_path,
                job.status,
                job.job_id,
                summary_json,
                job.routed_to,
                job.submitted_at,
                job.completed_at,
                job.error_message,
                share_links_json,
                job.jdf_path,
                job.batch_group,
                job.batch_id,
                job.next_retry_at,
                job.retry_attempts,
            ],
        )
        .map_err(|e| format!("Failed to insert job: {}", e))?;

        // Auto-prune: keep last 1000 terminal rows; never prune queued
        // rows (they still need to submit).
        conn.execute(
            "DELETE FROM jobs WHERE id NOT IN (
                SELECT id FROM jobs
                WHERE status IN ('queued_offline','queued_retry','processing')
                UNION
                SELECT id FROM jobs
                WHERE status NOT IN ('queued_offline','queued_retry','processing')
                ORDER BY submitted_at DESC LIMIT 1000
             )",
            [],
        )
        .ok();

        Ok(())
    }

    pub fn update_job(&self, job: &JobRecord) -> Result<(), String> {
        self.insert_job(job)
    }

    fn row_to_record(row: &rusqlite::Row<'_>) -> rusqlite::Result<JobRecord> {
        let summary_json: Option<String> = row.get(6)?;
        let summary =
            summary_json.and_then(|s| serde_json::from_str::<JobSummary>(&s).ok());
        let share_links_json: Option<String> = row.get(11)?;
        let share_links =
            share_links_json.and_then(|s| serde_json::from_str::<ShareLinks>(&s).ok());

        Ok(JobRecord {
            id: row.get(0)?,
            folder_id: row.get(1)?,
            file_name: row.get(2)?,
            file_path: row.get(3)?,
            status: row.get(4)?,
            job_id: row.get(5)?,
            summary,
            routed_to: row.get(7)?,
            submitted_at: row.get(8)?,
            completed_at: row.get(9)?,
            error_message: row.get(10)?,
            share_links,
            jdf_path: row.get(12)?,
            batch_group: row.get(13)?,
            batch_id: row.get(14)?,
            next_retry_at: row.get(15)?,
            retry_attempts: row.get::<_, i64>(16)? as u32,
        })
    }

    const SELECT_COLS: &'static str = "id, folder_id, file_name, file_path, \
        status, job_id, summary_json, routed_to, submitted_at, completed_at, \
        error_message, share_links_json, jdf_path, batch_group, batch_id, \
        next_retry_at, retry_attempts";

    pub fn get_recent(&self, limit: u32) -> Result<Vec<JobRecord>, String> {
        let conn = self.conn.lock().unwrap();
        let sql = format!(
            "SELECT {} FROM jobs ORDER BY submitted_at DESC LIMIT ?1",
            Self::SELECT_COLS
        );
        let mut stmt = conn
            .prepare(&sql)
            .map_err(|e| format!("Failed to prepare query: {}", e))?;

        let rows = stmt
            .query_map(params![limit], Self::row_to_record)
            .map_err(|e| format!("Failed to query jobs: {}", e))?;

        Ok(rows.flatten().collect())
    }

    pub fn get_by_local_id(&self, id: &str) -> Result<Option<JobRecord>, String> {
        let conn = self.conn.lock().unwrap();
        let sql = format!(
            "SELECT {} FROM jobs WHERE id = ?1 LIMIT 1",
            Self::SELECT_COLS
        );
        let mut stmt = conn
            .prepare(&sql)
            .map_err(|e| format!("Failed to prepare query: {}", e))?;

        let mut rows = stmt
            .query(params![id])
            .map_err(|e| format!("Failed to query job: {}", e))?;

        match rows.next().map_err(|e| e.to_string())? {
            Some(row) => Ok(Some(Self::row_to_record(row).map_err(|e| e.to_string())?)),
            None => Ok(None),
        }
    }

    /// Return rows that are waiting for submission and whose
    /// `next_retry_at` (if any) is in the past. Ordered by
    /// `submitted_at` so the drainer processes FIFO.
    pub fn get_queued_ready(&self, now_rfc3339: &str) -> Result<Vec<JobRecord>, String> {
        let conn = self.conn.lock().unwrap();
        let sql = format!(
            "SELECT {} FROM jobs
             WHERE status IN ('queued_offline','queued_retry')
               AND (next_retry_at IS NULL OR next_retry_at <= ?1)
             ORDER BY submitted_at ASC",
            Self::SELECT_COLS
        );
        let mut stmt = conn
            .prepare(&sql)
            .map_err(|e| format!("Failed to prepare query: {}", e))?;
        let rows = stmt
            .query_map(params![now_rfc3339], Self::row_to_record)
            .map_err(|e| format!("Failed to query queued jobs: {}", e))?;
        Ok(rows.flatten().collect())
    }

    /// Count everything that still needs to submit. Used by the
    /// connectivity monitor to decide whether a "Back online" toast is
    /// worth firing and by the UI status bar.
    pub fn count_queued(&self) -> Result<u32, String> {
        let conn = self.conn.lock().unwrap();
        let count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM jobs WHERE status IN \
                 ('queued_offline','queued_retry')",
                [],
                |row| row.get(0),
            )
            .map_err(|e| format!("Failed to count queued: {}", e))?;
        Ok(count as u32)
    }

    /// Return rows currently in `processing` — used at startup to
    /// resume polling for jobs that were mid-flight when the app last
    /// quit.
    pub fn get_in_flight(&self) -> Result<Vec<JobRecord>, String> {
        let conn = self.conn.lock().unwrap();
        let sql = format!(
            "SELECT {} FROM jobs WHERE status = 'processing' ORDER BY submitted_at ASC",
            Self::SELECT_COLS
        );
        let mut stmt = conn
            .prepare(&sql)
            .map_err(|e| format!("Failed to prepare query: {}", e))?;
        let rows = stmt
            .query_map([], Self::row_to_record)
            .map_err(|e| format!("Failed to query in-flight: {}", e))?;
        Ok(rows.flatten().collect())
    }

    pub fn clear(&self) -> Result<(), String> {
        let conn = self.conn.lock().unwrap();
        // Don't nuke queued / in-flight rows — those still owe the
        // user work.
        conn.execute(
            "DELETE FROM jobs WHERE status NOT IN \
             ('queued_offline','queued_retry','processing')",
            [],
        )
        .map_err(|e| format!("Failed to clear jobs: {}", e))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_is_queued_classifies_correctly() {
        assert!(status::is_queued(status::QUEUED_OFFLINE));
        assert!(status::is_queued(status::QUEUED_RETRY));
        assert!(!status::is_queued(status::PROCESSING));
        assert!(!status::is_queued(status::PASSED));
        assert!(!status::is_queued(status::FAILED));
        assert!(!status::is_queued(status::ERROR));
    }
}
