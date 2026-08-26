-- Face 2 Fate — Database Schema
-- Reconstructed from the queries used in app.py and pipeline.py.
-- Target: MySQL 8+
--
-- Usage:
--   mysql -u root -p < schema.sql
--
-- This creates the database and all tables the application code queries.
-- Note: the `questions` table is referenced only via a plain `q_id` value
-- in app.py/pipeline.py (no INSERT/SELECT on a `questions` table appears
-- in the code shown), so a minimal placeholder table is included here —
-- extend it with whatever columns your question bank actually needs.

CREATE DATABASE IF NOT EXISTS emotion_aware
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE emotion_aware;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  u_id       INT AUTO_INCREMENT PRIMARY KEY,
  username   VARCHAR(100) NOT NULL,
  email      VARCHAR(255) NOT NULL UNIQUE,
  password   VARCHAR(255) NOT NULL,   -- NOTE: app currently stores/compares this in
                                       -- plaintext; strongly recommend hashing
                                       -- (e.g. werkzeug.security.generate_password_hash)
                                       -- before going anywhere near production.
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- QUESTIONS (minimal placeholder — extend as needed)
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
  q_id       INT AUTO_INCREMENT PRIMARY KEY,
  question_text VARCHAR(500) NOT NULL,
  category   VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- VIDEO
-- ============================================================
CREATE TABLE IF NOT EXISTS video (
  v_id       INT AUTO_INCREMENT PRIMARY KEY,
  u_id       INT NOT NULL,
  q_id       INT NOT NULL,
  vid_path   VARCHAR(500) NOT NULL DEFAULT '',
  status     VARCHAR(20) NOT NULL DEFAULT 'processing',  -- 'processing' | 'done'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (u_id) REFERENCES users(u_id) ON DELETE CASCADE,
  FOREIGN KEY (q_id) REFERENCES questions(q_id) ON DELETE CASCADE,
  INDEX idx_video_qid_uid (q_id, u_id)
) ENGINE=InnoDB;

-- ============================================================
-- VIDEO_ANALYSIS  (1:1 with video)
-- ============================================================
CREATE TABLE IF NOT EXISTS video_analysis (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  v_id                 INT NOT NULL,
  eye_contact_percent  FLOAT,
  blink_rate           FLOAT,
  emotion_distribution JSON,
  hand_movement        FLOAT,
  FOREIGN KEY (v_id) REFERENCES video(v_id) ON DELETE CASCADE,
  UNIQUE KEY uq_video_analysis_vid (v_id)
) ENGINE=InnoDB;

-- ============================================================
-- AUDIO_ANALYSIS  (1:1 with video)
-- ============================================================
CREATE TABLE IF NOT EXISTS audio_analysis (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  v_id       INT NOT NULL,
  duration   FLOAT,
  energy_var FLOAT,
  pitch_var  FLOAT,
  FOREIGN KEY (v_id) REFERENCES video(v_id) ON DELETE CASCADE,
  UNIQUE KEY uq_audio_analysis_vid (v_id)
) ENGINE=InnoDB;

-- ============================================================
-- TEXT_ANALYSIS  (1:1 with video)
-- ============================================================
CREATE TABLE IF NOT EXISTS text_analysis (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  v_id           INT NOT NULL,
  filler_events  JSON,
  filler_count   INT,
  transcript     LONGTEXT,
  FOREIGN KEY (v_id) REFERENCES video(v_id) ON DELETE CASCADE,
  UNIQUE KEY uq_text_analysis_vid (v_id)
) ENGINE=InnoDB;

-- ============================================================
-- REPORT  (1:1 with video)
-- ============================================================
CREATE TABLE IF NOT EXISTS report (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  v_id          INT NOT NULL,
  score         FLOAT,
  breakdown     JSON,
  main_feedback TEXT,
  FOREIGN KEY (v_id) REFERENCES video(v_id) ON DELETE CASCADE,
  UNIQUE KEY uq_report_vid (v_id)
) ENGINE=InnoDB;
