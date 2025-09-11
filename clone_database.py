import sqlite3
import json
import string
import random
from typing import Dict, Any, Optional

class CloneDatabase:
    def __init__(self, db_path: str = "AIAnalyzer.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database and create clonedRepo table"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS clonedRepo (
                    repoID TEXT PRIMARY KEY,
                    repo_name TEXT NOT NULL,
                    repo_url TEXT NOT NULL,
                    clone_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS AnalyzeRepo (
                    repoID TEXT PRIMARY KEY,
                    projectPath TEXT NOT NULL,
                    codelang TEXT,
                    aiAnalysis TEXT NOT NULL,
                    bedrockModel TEXT NOT NULL,
                    database TEXT,
                    databaseport NUMERIC,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS docker_status (
                    repoID TEXT PRIMARY KEY,
                    project_path TEXT,
                    status TEXT DEFAULT None,
                    imageID TEXT,
                    image_name TEXT,
                    error TEXT
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_repo_name ON clonedRepo(repo_name)
            ''')
            # conn.execute('''
            #     CREATE INDEX IF NOT EXISTS idx_repo_name ON clonedRepo(repo_name)
            # ''')
        finally:
            if conn:
                conn.close()
    
    def _generate_repo_id(self) -> str:
        """Generate unique 10-character alphanumeric string"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    def store_cloned_repo(self, repo_name: str, repo_url: str, clone_path: str, status: str = "success") -> str:
        """Store or update cloned repository data and return repoID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            conn.execute('PRAGMA journal_mode=WAL')
            
            # Check if repo_name already exists
            cursor = conn.execute('SELECT repoID FROM clonedRepo WHERE repo_name = ?', (repo_name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                repo_id = existing[0]
                conn.execute('''
                    UPDATE clonedRepo SET repo_url = ?, clone_path = ?, status = ?, modified_at = CURRENT_TIMESTAMP
                    WHERE repo_name = ?
                ''', (repo_url, clone_path, status, repo_name))
            else:
                # Insert new record
                repo_id = self._generate_repo_id()
                conn.execute('''
                    INSERT INTO clonedRepo (repoID, repo_name, repo_url, clone_path, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (repo_id, repo_name, repo_url, clone_path, status))
            
            return repo_id
        except Exception as e:
            print(f"Error storing cloned repo: {str(e)}")
            return ""
        finally:
            if conn:
                conn.close()
    
    def get_cloned_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cloned repository data by repoID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.execute(
                'SELECT repoID, repo_name, repo_url, clone_path, status, modified_at FROM clonedRepo WHERE repoID = ?',
                (repo_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    "repoID": result[0],
                    "repo_name": result[1],
                    "repo_url": result[2],
                    "clone_path": result[3],
                    "status": result[4],
                    "modified_at": result[5]
                }
            return None
        except Exception as e:
            print(f"Error retrieving cloned repo: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_all_cloned_repos(self) -> list:
        """Get all cloned repositories with analysis data"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.execute('''
                SELECT c.repoID, c.repo_name, c.repo_url, c.clone_path, c.status, c.modified_at,
                       a.projectPath, a.codelang, a.aiAnalysis, a.bedrockModel, a.database, a.databaseport
                FROM clonedRepo c
                LEFT JOIN AnalyzeRepo a ON c.repoID = a.repoID
                ORDER BY c.modified_at DESC
            ''')
            results = cursor.fetchall()
            repos = []
            for result in results:
                repos.append({
                    "repoID": result[0],
                    "repo_name": result[1],
                    "repo_url": result[2],
                    "clone_path": result[3],
                    "status": result[4],
                    "created_at": result[5],
                    "analysis": {
                        "projectPath": result[6],
                        "codelang": result[7],
                        "aiAnalysis": result[8],
                        "bedrockModel": result[9],
                        "database": result[10],
                        "databaseport": result[11]
                    } if result[6] else None
                })
            return repos
        except Exception as e:
            print(f"Error retrieving all repos: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()
    
    def store_analyze_repo(self, repo_id: str, analysis_data: Dict[str, Any]) -> bool:
        """Store or update repository analysis data"""
        conn = None
        try:
            print("analyze DB called")
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            conn.execute('PRAGMA journal_mode=WAL')
            
            # Check if repoID already exists
            cursor = conn.execute('SELECT repoID FROM AnalyzeRepo WHERE repoID = ?', (repo_id,))
            existing = cursor.fetchone()
            print(analysis_data)
            if existing:
                print("updating")
                # Update existing record
                conn.execute('''
                    UPDATE AnalyzeRepo SET projectPath = ?, codelang = ?, aiAnalysis = ?,
                    bedrockModel = ?, database = ?, databaseport = ?, modified_at = CURRENT_TIMESTAMP
                    WHERE repoID = ?
                ''', (
                    analysis_data.get('projectPath', ''),
                    json.dumps(analysis_data.get('codelang', '')),
                    analysis_data.get('aiAnalysis', ''),
                    analysis_data.get('bedrockModel', ''),
                    analysis_data.get('database', ''),
                    analysis_data.get('databaseport', 0),
                    repo_id
                ))
            else:
                print("inserting")
                # Insert new record
                conn.execute('''
                    INSERT INTO AnalyzeRepo (repoID, projectPath, codelang, aiAnalysis, bedrockModel, database, databaseport)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    repo_id,
                    analysis_data.get('projectPath', ''),
                    json.dumps(analysis_data.get('codelang', '')),
                    analysis_data.get('aiAnalysis', ''),
                    analysis_data.get('bedrockModel', ''),
                    analysis_data.get('database', ''),
                    analysis_data.get('databaseport', 0)
                ))
            
            return True
        except Exception as e:
            print(f"Error storing analyze repo: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def store_docker_status(self, repo_id: str, docker_data: Dict[str, Any]) -> bool:
        """Store or update docker status data"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            conn.execute('PRAGMA journal_mode=WAL')
            
            # Check if repoID already exists
            cursor = conn.execute('SELECT repoID FROM docker_status WHERE repoID = ?', (repo_id,))
            existing = cursor.fetchone()
            
            if existing:
                print("existing!")
                # Update existing record
                conn.execute('''
                    UPDATE docker_status SET project_path = ?, status = ?, imageID = ?, 
                    image_name = ?, error = ?
                    WHERE repoID = ?
                ''', (
                    docker_data.get('project_path', ''),
                    docker_data.get('status', ''),
                    docker_data.get('imageID', ''),
                    docker_data.get('image_name', ''),
                    docker_data.get('error', ''),
                    repo_id
                ))
            else:
                print("inserting!")
                print(repo_id)
                print(docker_data)
                # Insert new record
                conn.execute('''
                    INSERT INTO docker_status (repoID, project_path, status, imageID, image_name, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    repo_id,
                    docker_data.get('project_path', ''),
                    docker_data.get('status', ''),
                    docker_data.get('imageID', ''),
                    docker_data.get('image_name', ''),
                    docker_data.get('error', '')
                ))
            
            return True
        except Exception as e:
            print(f"Error storing docker status: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    
    def close(self):
        """Close database connection"""
        pass