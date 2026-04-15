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
}

impl ShareLinks {
    pub fn is_empty(&self) -> bool {
        self.html.is_none()
            && self.pdf.is_none()
            && self.json.is_none()
            && self.xml.is_none()
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
                share_links_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_submitted ON jobs(submitted_at DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_folder ON jobs(folder_id);",
        )
        .map_err(|e| format!("Failed to create tables: {}", e))?;

        // Idempotent migration for DBs created before share_links_json existed.
        // SQLite returns an error if the column already exists — treat that as a no-op.
        if let Err(e) = conn.execute("ALTER TABLE jobs ADD COLUMN share_links_json TEXT", []) {
            let msg = e.to_string();
            if !msg.contains("duplicate column name") {
                log::warn!("share_links_json migration: {}", msg);
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
            "INSERT OR REPLACE INTO jobs (id, folder_id, file_name, file_path, status, job_id, summary_json, routed_to, submitted_at, completed_at, error_message, share_links_json)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
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
            ],
        )
        .map_err(|e| format!("Failed to insert job: {}", e))?;

        // Auto-prune: keep last 1000
        conn.execute(
            "DELETE FROM jobs WHERE id NOT IN (SELECT id FROM jobs ORDER BY submitted_at DESC LIMIT 1000)",
            [],
        )
        .ok();

        Ok(())
    }

    pub fn update_job(&self, job: &JobRecord) -> Result<(), String> {
        self.insert_job(job)
    }

    pub fn get_recent(&self, limit: u32) -> Result<Vec<JobRecord>, String> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare(
                "SELECT id, folder_id, file_name, file_path, status, job_id, summary_json, routed_to, submitted_at, completed_at, error_message, share_links_json
                 FROM jobs ORDER BY submitted_at DESC LIMIT ?1",
            )
            .map_err(|e| format!("Failed to prepare query: {}", e))?;

        let rows = stmt
            .query_map(params![limit], |row| {
                let summary_json: Option<String> = row.get(6)?;
                let summary = summary_json
                    .and_then(|s| serde_json::from_str::<JobSummary>(&s).ok());
                let share_links_json: Option<String> = row.get(11)?;
                let share_links = share_links_json
                    .and_then(|s| serde_json::from_str::<ShareLinks>(&s).ok());

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
                })
            })
            .map_err(|e| format!("Failed to query jobs: {}", e))?;

        let mut jobs = Vec::new();
        for row in rows {
            if let Ok(job) = row {
                jobs.push(job);
            }
        }
        Ok(jobs)
    }

    pub fn get_by_local_id(&self, id: &str) -> Result<Option<JobRecord>, String> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare(
                "SELECT id, folder_id, file_name, file_path, status, job_id, summary_json, routed_to, submitted_at, completed_at, error_message, share_links_json
                 FROM jobs WHERE id = ?1 LIMIT 1",
            )
            .map_err(|e| format!("Failed to prepare query: {}", e))?;

        let mut rows = stmt
            .query(params![id])
            .map_err(|e| format!("Failed to query job: {}", e))?;

        if let Some(row) = rows.next().map_err(|e| e.to_string())? {
            let summary_json: Option<String> = row.get(6).map_err(|e| e.to_string())?;
            let summary = summary_json
                .and_then(|s| serde_json::from_str::<JobSummary>(&s).ok());
            let share_links_json: Option<String> = row.get(11).map_err(|e| e.to_string())?;
            let share_links = share_links_json
                .and_then(|s| serde_json::from_str::<ShareLinks>(&s).ok());

            Ok(Some(JobRecord {
                id: row.get(0).map_err(|e| e.to_string())?,
                folder_id: row.get(1).map_err(|e| e.to_string())?,
                file_name: row.get(2).map_err(|e| e.to_string())?,
                file_path: row.get(3).map_err(|e| e.to_string())?,
                status: row.get(4).map_err(|e| e.to_string())?,
                job_id: row.get(5).map_err(|e| e.to_string())?,
                summary,
                routed_to: row.get(7).map_err(|e| e.to_string())?,
                submitted_at: row.get(8).map_err(|e| e.to_string())?,
                completed_at: row.get(9).map_err(|e| e.to_string())?,
                error_message: row.get(10).map_err(|e| e.to_string())?,
                share_links,
            }))
        } else {
            Ok(None)
        }
    }

    pub fn clear(&self) -> Result<(), String> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM jobs", [])
            .map_err(|e| format!("Failed to clear jobs: {}", e))?;
        Ok(())
    }
}
