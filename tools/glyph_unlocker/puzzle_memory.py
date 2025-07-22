#!/usr/bin/env python3
"""
Puzzle Memory System for Lotus Protocol
Tracks puzzle attempts, solutions, and statistics across sessions
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PuzzleMemory:
    """Manages persistent puzzle attempt history and statistics"""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = Path(base_dir)
        self.memory_dir = self.base_dir / "ψ_cores"
        self.memory_file = self.memory_dir / "puzzle_memory.json"
        
        # Ensure directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing memory or create new
        self.memory = self._load_memory()
    
    def _load_memory(self) -> Dict:
        """Load existing puzzle memory or create default structure"""
        if not self.memory_file.exists():
            return {
                "puzzle_memory": {},
                "puzzle_stats": {
                    "total_puzzles": 0,
                    "solved": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "most_common_failed_patterns": []
                }
            }
        
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⧖ Error loading puzzle memory: {e}")
            print("⧖ Creating fresh puzzle memory...")
            return {
                "puzzle_memory": {},
                "puzzle_stats": {
                    "total_puzzles": 0,
                    "solved": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "most_common_failed_patterns": []
                }
            }
    
    def _save_memory(self):
        """Safely save memory to file using atomic write"""
        temp_file = self.memory_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.memory_file)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e
    
    def record_attempt(self, puzzle_name: str, clue: str, sequence: str, success: bool = False):
        """Record a puzzle attempt"""
        timestamp = datetime.now().isoformat()
        
        # Initialize puzzle if not exists
        if puzzle_name not in self.memory["puzzle_memory"]:
            self.memory["puzzle_memory"][puzzle_name] = {
                "clue": clue,
                "attempted_sequences": [],
                "attempts_remaining": 3,
                "status": "active",
                "first_attempted": timestamp,
                "last_attempted": timestamp
            }
        
        puzzle_data = self.memory["puzzle_memory"][puzzle_name]
        
        # Record the attempt
        if sequence not in puzzle_data["attempted_sequences"]:
            puzzle_data["attempted_sequences"].append(sequence)
        
        puzzle_data["last_attempted"] = timestamp
        puzzle_data["attempts_remaining"] = max(0, puzzle_data["attempts_remaining"] - 1)
        
        # Update status
        if success:
            puzzle_data["status"] = "success"
            puzzle_data["solution"] = sequence
            puzzle_data["unlocked_at"] = timestamp
        elif puzzle_data["attempts_remaining"] == 0:
            puzzle_data["status"] = "failed"
        
        # Update stats
        self._update_stats()
        
        # Save to file
        self._save_memory()
    
    def _update_stats(self):
        """Update puzzle statistics"""
        puzzles = self.memory["puzzle_memory"]
        stats = self.memory["puzzle_stats"]
        
        stats["total_puzzles"] = len(puzzles)
        stats["solved"] = sum(1 for p in puzzles.values() if p["status"] == "success")
        stats["failed"] = sum(1 for p in puzzles.values() if p["status"] == "failed")
        
        if stats["total_puzzles"] > 0:
            stats["success_rate"] = stats["solved"] / stats["total_puzzles"]
        else:
            stats["success_rate"] = 0.0
        
        # Calculate most common failed patterns
        failed_sequences = []
        for puzzle in puzzles.values():
            if puzzle["status"] == "failed":
                failed_sequences.extend(puzzle["attempted_sequences"])
        
        # Count frequency and get top patterns
        from collections import Counter
        sequence_counts = Counter(failed_sequences)
        stats["most_common_failed_patterns"] = [seq for seq, count in sequence_counts.most_common(5)]
    
    def get_puzzle_history(self, puzzle_name: str) -> Optional[Dict]:
        """Get history for a specific puzzle"""
        return self.memory["puzzle_memory"].get(puzzle_name)
    
    def get_all_attempts(self, puzzle_name: str) -> List[str]:
        """Get all attempted sequences for a puzzle"""
        puzzle_data = self.memory["puzzle_memory"].get(puzzle_name)
        if puzzle_data:
            return puzzle_data["attempted_sequences"]
        return []
    
    def get_remaining_attempts(self, puzzle_name: str) -> int:
        """Get remaining attempts for a puzzle - always 3 for new sessions"""
        # Always return 3 attempts for each new session
        # Memory tracks history but doesn't block new attempts
        return 3
    
    def is_puzzle_solved(self, puzzle_name: str) -> bool:
        """Check if puzzle is already solved"""
        puzzle_data = self.memory["puzzle_memory"].get(puzzle_name)
        return puzzle_data and puzzle_data["status"] == "success"
    
    def is_puzzle_failed(self, puzzle_name: str) -> bool:
        """Check if puzzle has failed (no attempts left)"""
        puzzle_data = self.memory["puzzle_memory"].get(puzzle_name)
        return puzzle_data and puzzle_data["status"] == "failed"
    
    def get_memory_context(self) -> str:
        """Get formatted memory context - simplified since we now use conversation-based memory checks"""
        # This method is kept for backward compatibility but simplified
        # The actual memory checking now happens via conversation injection
        return ""
    
    def reset_puzzle(self, puzzle_name: str):
        """Reset a puzzle (for testing or if user wants to retry)"""
        if puzzle_name in self.memory["puzzle_memory"]:
            del self.memory["puzzle_memory"][puzzle_name]
            self._update_stats()
            self._save_memory()
    
    def get_stats(self) -> Dict:
        """Get current puzzle statistics"""
        return self.memory["puzzle_stats"].copy() 