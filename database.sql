-- ============================================================
-- NATIONAL SCHEME FRAUD PORTAL — NSFP v2.0
-- database.sql | Developed by Sona Choudhary | 2026
-- ============================================================

CREATE DATABASE IF NOT EXISTS gov_ai_fraud
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gov_ai_fraud;

-- ─── STATES TABLE ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS states (
    state_id    INT AUTO_INCREMENT PRIMARY KEY,
    state_name  VARCHAR(100) NOT NULL,
    state_code  VARCHAR(5),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO states (state_name, state_code) VALUES
    ('Rajasthan', 'RJ'),
    ('Uttar Pradesh', 'UP'),
    ('Madhya Pradesh', 'MP'),
    ('Delhi', 'DL'),
    ('Bihar', 'BR'),
    ('Haryana', 'HR'),
    ('Gujarat', 'GJ'),
    ('Karnataka', 'KA')
ON DUPLICATE KEY UPDATE state_name = VALUES(state_name);

-- ─── ADMIN USERS TABLE ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_users (
    admin_id       INT AUTO_INCREMENT PRIMARY KEY,
    username       VARCHAR(50) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(100),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login     TIMESTAMP NULL
) ENGINE=InnoDB;

-- Default admin: username=sona2026, password=Papa9829
DELETE FROM admin_users WHERE username <> 'sona2026';

INSERT INTO admin_users (username, password_hash, full_name)
VALUES ('sona2026', SHA2('Papa9829', 256), 'Sona Choudhary')
ON DUPLICATE KEY UPDATE
    password_hash = VALUES(password_hash),
    full_name = VALUES(full_name);

-- ─── BENEFICIARIES TABLE ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS beneficiaries (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    aadhaar           BIGINT NOT NULL,
    age               TINYINT UNSIGNED NOT NULL,
    income            INT UNSIGNED NOT NULL,
    schemes_taken     TINYINT UNSIGNED NOT NULL DEFAULT 0,
    fraud_predicted   TINYINT(1) NOT NULL DEFAULT 0,
    confidence_score  FLOAT,
    state_id          INT NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (state_id) REFERENCES states(state_id) ON DELETE RESTRICT,
    INDEX idx_fraud    (fraud_predicted),
    INDEX idx_state    (state_id),
    INDEX idx_created  (created_at)
) ENGINE=InnoDB;

-- ─── AUDIT LOG TABLE ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    admin_user  VARCHAR(50),
    action      VARCHAR(100),
    details     TEXT,
    ip_address  VARCHAR(45),
    logged_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (admin_user),
    INDEX idx_time (logged_at)
) ENGINE=InnoDB;
