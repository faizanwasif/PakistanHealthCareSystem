import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os
from config.config import config

logger = logging.getLogger(__name__)

class OfflineManager:
    def __init__(self):
        self.db_path = "offline_cache.db"
        self.connection_status = "online"
        self.last_sync = None
        self._init_offline_db()
    
    def _init_offline_db(self):
        """Initialize SQLite database for offline caching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for offline data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facilities (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                location_lat REAL,
                location_lng REAL,
                services TEXT,
                sehat_card_accepted INTEGER,
                cached_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medical_rules (
                id TEXT PRIMARY KEY,
                symptoms TEXT,
                urgency_level TEXT,
                recommendations TEXT,
                cached_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                messages TEXT,
                created_at TEXT,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Offline database initialized")
    
    def offline_triage(self, symptoms: List[str]) -> Dict[str, Any]:
        """Perform basic triage using cached rules"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find matching rules
        best_match = None
        max_matches = 0
        
        cursor.execute('SELECT * FROM medical_rules')
        for row in cursor.fetchall():
            rule_symptoms = json.loads(row[1])
            matches = len(set(symptoms).intersection(set(rule_symptoms)))
            
            if matches > max_matches:
                max_matches = matches
                best_match = {
                    'urgency_level': row[2],
                    'recommendations': json.loads(row[3]),
                    'confidence': matches / len(symptoms) if symptoms else 0
                }
        
        conn.close()
        
        if best_match:
            return {
                'urgency_level': best_match['urgency_level'],
                'recommendations': best_match['recommendations'],
                'confidence': best_match['confidence'],
                'mode': 'offline'
            }
        else:
            return {
                'urgency_level': 'medium',
                'recommendations': ['Seek medical attention when connectivity is restored'],
                'confidence': 0.1,
                'mode': 'offline'
            }
    
    def set_connection_status(self, status: str):
        """Update connection status"""
        self.connection_status = status
        logger.info(f"Connection status: {status}")

# Global offline manager
offline_manager = OfflineManager()
