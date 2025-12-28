-- Migration script to add meeting_room_url column to meetings table
-- Run this if you have existing data and need to add the new column

-- For PostgreSQL
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_room_url VARCHAR(500);

-- For SQLite (if using SQLite)
-- ALTER TABLE meetings ADD COLUMN meeting_room_url VARCHAR(500);

-- Note: If using SQLAlchemy's Base.metadata.create_all(), the column will be added automatically
-- This script is only needed if you're manually managing migrations

