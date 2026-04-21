-- Migration: 001_initial_schema
-- Description: Initial database schema with all core tables
-- Version: 1.0.0
-- Date: 2024

-- This migration creates the initial database schema
-- Run this migration on a fresh database

\echo 'Running migration 001_initial_schema...'

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Import the enhanced schema
\i ../schema_enhanced.sql

\echo 'Migration 001_initial_schema completed successfully!'
