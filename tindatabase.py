from tinydb import TinyDB, Query
from typing import Dict, Any, Optional
import json

class RepoDatabase:
    def __init__(self, db_path: str = "repoDB.json"):
        self.db = TinyDB(db_path)
        self.repos_table = self.db.table('repos')
    
    def store_repo_analysis(self, repo_name: str, analysis_data: Dict[str, Any]) -> bool:
        """Store repository analysis data with repo_name as key"""
        try:
            # Clear all existing data and store as single document with repo names as keys
            existing_data = {}
            all_docs = self.repos_table.all()
            for doc in all_docs:
                for key, value in doc.items():
                    if key != repo_name:  # Keep other repos
                        existing_data[key] = value
            
            # Add/update current repo
            existing_data[repo_name] = analysis_data
            
            # Clear table and insert single document
            self.repos_table.truncate()
            self.repos_table.insert(existing_data)
            return True
        except Exception as e:
            print(f"Error storing repo analysis: {str(e)}")
            return False
    
    def get_repo_analysis(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve repository analysis data by repo_name"""
        try:
            all_docs = self.repos_table.all()
            if all_docs and repo_name in all_docs[0]:
                return all_docs[0][repo_name]
            return None
        except Exception as e:
            print(f"Error retrieving repo analysis: {str(e)}")
            return None
    
    def get_all_repos(self) -> Dict[str, Any]:
        """Get all stored repository analyses"""
        try:
            all_docs = self.repos_table.all()
            if all_docs:
                return all_docs[0]
            return {}
        except Exception as e:
            print(f"Error retrieving all repos: {str(e)}")
            return {}
    
    def delete_repo(self, repo_name: str) -> bool:
        """Delete repository analysis by repo_name"""
        try:
            Repo = Query()
            self.repos_table.remove(Repo.repo_name == repo_name)
            return True
        except Exception as e:
            print(f"Error deleting repo: {str(e)}")
            return False
    
    def close(self):
        """Close database connection"""
        self.db.close()