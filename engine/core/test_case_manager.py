"""
test_case_manager.py — Test Case Management for Magical Test Tool
Manages generation, storage, and retrieval of AI-generated test cases
with detailed explanations and execution history.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid

from core.db import get_connection, init_db

class TestCaseManager:
    """Manages AI-generated test cases with explanations and execution history."""
    
    def __init__(self):
        """Initialize TestCaseManager with database connection."""
        self.db_path = Path("/tmp/database_v4.sqlite")
        self._init_test_case_tables()
    
    def _init_test_case_tables(self):
        """Create tables for test cases if they don't exist."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Test Cases Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS magic_test_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    steps TEXT NOT NULL,
                    explanations TEXT NOT NULL,
                    risk_level TEXT DEFAULT 'medium',
                    tags TEXT,
                    status TEXT DEFAULT 'created',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test Case Executions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS magic_test_case_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    execution_id TEXT UNIQUE NOT NULL,
                    status TEXT,
                    duration_ms INTEGER,
                    passed_steps INTEGER,
                    failed_steps INTEGER,
                    screenshots TEXT,
                    error_message TEXT,
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES magic_test_cases(test_id)
                )
            """)
            
            # Monkey Test Findings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS magic_monkey_test_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    mode TEXT,
                    iterations INTEGER,
                    findings TEXT NOT NULL,
                    anomalies TEXT,
                    generated_test_ids TEXT,
                    duration_ms INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test Strategy Analyses Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS magic_test_strategy_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    page_type TEXT,
                    complexity_score REAL,
                    critical_elements TEXT,
                    recommendations TEXT,
                    best_practices TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def create_test_case(self, url: str, title: str, steps: List[Dict], 
                        explanations: List[str], description: str = None,
                        risk_level: str = "medium", tags: List[str] = None) -> str:
        """
        Create and store a new test case with explanations.
        
        Args:
            url: URL of the page being tested
            title: Test case title
            steps: List of test steps (each step is a dict with action, selector, value)
            explanations: Detailed explanations for each step
            description: Optional test case description
            risk_level: Risk level (low, medium, high)
            tags: Optional tags for categorization
        
        Returns:
            test_id: Unique identifier for the test case
        """
        test_id = f"test_{uuid.uuid4().hex[:12]}"
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magic_test_cases 
                (test_id, url, title, description, steps, explanations, risk_level, tags, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'created')
            """, (
                test_id,
                url,
                title,
                description,
                json.dumps(steps),
                json.dumps(explanations),
                risk_level,
                json.dumps(tags) if tags else None
            ))
            conn.commit()
        
        return test_id
    
    def get_test_case(self, test_id: str) -> Optional[Dict]:
        """Retrieve a test case by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM magic_test_cases WHERE test_id = ?
            """, (test_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'test_id': row['test_id'],
                    'url': row['url'],
                    'title': row['title'],
                    'description': row['description'],
                    'steps': json.loads(row['steps']),
                    'explanations': json.loads(row['explanations']),
                    'risk_level': row['risk_level'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'status': row['status'],
                    'created_at': row['created_at']
                }
        return None
    
    def list_test_cases(self, url: str = None, limit: int = 50) -> List[Dict]:
        """
        List test cases with optional filtering.
        
        Args:
            url: Optional URL filter
            limit: Maximum number of results
        
        Returns:
            List of test cases
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if url:
                cursor.execute("""
                    SELECT * FROM magic_test_cases 
                    WHERE url = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (url, limit))
            else:
                cursor.execute("""
                    SELECT * FROM magic_test_cases 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [
                {
                    'test_id': row['test_id'],
                    'title': row['title'],
                    'url': row['url'],
                    'risk_level': row['risk_level'],
                    'status': row['status'],
                    'created_at': row['created_at']
                }
                for row in rows
            ]
    
    def record_execution(self, test_id: str, status: str, duration_ms: int = 0,
                        passed_steps: int = 0, failed_steps: int = 0,
                        screenshots: List[str] = None, error_message: str = None) -> str:
        """
        Record execution result of a test case.
        
        Args:
            test_id: Test case ID
            status: Execution status (passed, failed, error)
            duration_ms: Execution duration in milliseconds
            passed_steps: Number of passed steps
            failed_steps: Number of failed steps
            screenshots: List of screenshot paths
            error_message: Optional error message
        
        Returns:
            execution_id: Unique identifier for the execution
        """
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magic_test_case_executions
                (test_id, execution_id, status, duration_ms, passed_steps, failed_steps, screenshots, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
                execution_id,
                status,
                duration_ms,
                passed_steps,
                failed_steps,
                json.dumps(screenshots) if screenshots else None,
                error_message
            ))
            conn.commit()
        
        return execution_id
    
    def record_monkey_test(self, url: str, mode: str, iterations: int,
                          findings: List[Dict], anomalies: List[Dict] = None,
                          generated_test_ids: List[str] = None, duration_ms: int = 0) -> str:
        """
        Record monkey testing session results.
        
        Args:
            url: URL tested
            mode: Testing mode (random, smart, hybrid)
            iterations: Number of interactions
            findings: List of findings (interactions, behaviors)
            anomalies: List of detected anomalies
            generated_test_ids: Test IDs generated from findings
            duration_ms: Session duration in milliseconds
        
        Returns:
            session_id: Unique identifier for the monkey testing session
        """
        session_id = f"monkey_{uuid.uuid4().hex[:12]}"
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magic_monkey_test_findings
                (session_id, url, mode, iterations, findings, anomalies, generated_test_ids, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                url,
                mode,
                iterations,
                json.dumps(findings),
                json.dumps(anomalies) if anomalies else None,
                json.dumps(generated_test_ids) if generated_test_ids else None,
                duration_ms
            ))
            conn.commit()
        
        return session_id
    
    def record_strategy_analysis(self, url: str, page_type: str, complexity_score: float,
                                critical_elements: List[str], recommendations: List[str],
                                best_practices: List[str]) -> str:
        """
        Record page strategy analysis results.
        
        Args:
            url: URL analyzed
            page_type: Detected page type (login, checkout, dashboard, etc.)
            complexity_score: Page complexity (0-10)
            critical_elements: List of critical UI elements
            recommendations: Test recommendations
            best_practices: Relevant best practices
        
        Returns:
            analysis_id: Unique identifier for the analysis
        """
        analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magic_test_strategy_analyses
                (analysis_id, url, page_type, complexity_score, critical_elements, recommendations, best_practices)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                url,
                page_type,
                complexity_score,
                json.dumps(critical_elements),
                json.dumps(recommendations),
                json.dumps(best_practices)
            ))
            conn.commit()
        
        return analysis_id
    
    def get_execution_history(self, test_id: str) -> List[Dict]:
        """Get execution history for a test case."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM magic_test_case_executions 
                WHERE test_id = ? 
                ORDER BY executed_at DESC
            """, (test_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'execution_id': row['execution_id'],
                    'status': row['status'],
                    'duration_ms': row['duration_ms'],
                    'passed_steps': row['passed_steps'],
                    'failed_steps': row['failed_steps'],
                    'executed_at': row['executed_at']
                }
                for row in rows
            ]
    
    def export_test_case_to_gherkin(self, test_id: str) -> str:
        """
        Export test case to Gherkin format.
        
        Args:
            test_id: Test case ID
        
        Returns:
            Gherkin feature file content
        """
        test_case = self.get_test_case(test_id)
        if not test_case:
            return None
        
        gherkin = f"""Feature: {test_case['title']}
  {test_case['description'] or ''}

  Scenario: {test_case['title']}
    Given kullanıcı "{test_case['url']}" sayfasındadır
"""
        
        for i, (step, explanation) in enumerate(zip(test_case['steps'], test_case['explanations'])):
            gherkin += f"    # Step {i+1}: {explanation}\n"
            
            if step.get('action') == 'click':
                gherkin += f"    When kullanıcı \"{step.get('selector')}\" düğmesine tıklar\n"
            elif step.get('action') == 'fill':
                gherkin += f"    When kullanıcı \"{step.get('selector')}\" kutusuna \"{step.get('value')}\" yazar\n"
            elif step.get('action') == 'assert':
                gherkin += f"    Then \"{step.get('selector')}\" elementi görunur olmalıdır\n"
        
        return gherkin


# Initialize tables on import
init_db()
