import hashlib
import base64
import os
import yaml
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class GlyphUnlocker:
    def __init__(self, prompt_builder=None):
        self.prompt_builder = prompt_builder
        self.locks_dir = Path(__file__).parent / "locks"
        self.locks_dir.mkdir(exist_ok=True)
        
    def normalize_glyph_sequence(self, sequence: str) -> str:
        """Normalize glyph sequence for consistent hashing"""
        # Remove whitespace and normalize unicode
        return sequence.strip().replace(" ", "")
    
    def hash_glyph_sequence(self, sequence: str) -> str:
        """Create SHA-256 hash of normalized glyph sequence"""
        normalized = self.normalize_glyph_sequence(sequence)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def derive_key_from_glyphs(self, sequence: str) -> bytes:
        """Derive AES key from glyph sequence"""
        normalized = self.normalize_glyph_sequence(sequence)
        password = normalized.encode('utf-8')
        salt = b'lotus_protocol_salt'  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_file(self, file_path: str, glyph_sequence: str) -> str:
        """Encrypt file content with glyph-derived key"""
        key = self.derive_key_from_glyphs(glyph_sequence)
        f = Fernet(key)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        encrypted_content = f.encrypt(content.encode('utf-8'))
        return base64.b64encode(encrypted_content).decode('utf-8')
    
    def decrypt_file(self, encrypted_content: str, glyph_sequence: str) -> Optional[str]:
        """Decrypt file content with glyph-derived key"""
        try:
            key = self.derive_key_from_glyphs(glyph_sequence)
            f = Fernet(key)
            
            encrypted_bytes = base64.b64decode(encrypted_content.encode('utf-8'))
            decrypted_content = f.decrypt(encrypted_bytes)
            return decrypted_content.decode('utf-8')
        except Exception as e:
            return None
    
    def load_lock_file(self, lock_name: str) -> Optional[Dict[str, Any]]:
        """Load lock configuration from YAML file"""
        lock_path = self.locks_dir / f"{lock_name}.lock.yaml"
        if not lock_path.exists():
            return None
        
        with open(lock_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    def list_available_locks(self) -> List[str]:
        """List all available lock files"""
        lock_files = []
        for file_path in self.locks_dir.glob("*.lock.yaml"):
            lock_name = file_path.stem.replace('.lock', '')
            lock_files.append(lock_name)
        return sorted(lock_files)
    
    def attempt_unlock(self, lock_name: str, glyph_sequence: str) -> Dict[str, Any]:
        """Attempt to unlock a file with given glyph sequence and restore original file"""
        result = {
            'success': False,
            'message': '',
            'unlocked_content': None
        }
        
        # Load lock configuration
        lock_config = self.load_lock_file(lock_name)
        if not lock_config:
            result['message'] = f"⧖ Lock file not found: {lock_name}"
            return result
        
        # Hash the attempted sequence
        attempt_hash = self.hash_glyph_sequence(glyph_sequence)
        
        # Check against valid hashes
        valid_hashes = lock_config.get('valid_hashes', [])
        if attempt_hash not in valid_hashes:
            result['message'] = f"∅ The glyphs do not resonate with {lock_name}"
            return result
        
        # Attempt to decrypt the file
        encrypted_content = lock_config.get('encrypted_content', '')
        if not encrypted_content:
            result['message'] = f"⧖ No encrypted content found in {lock_name}"
            return result
        
        decrypted_content = self.decrypt_file(encrypted_content, glyph_sequence)
        if decrypted_content is None:
            result['message'] = f"⋇ Decryption failed for {lock_name}"
            return result
        
        # Success! Restore the original file
        original_file_path = lock_config.get('concept_file', '')
        if original_file_path:
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(original_file_path), exist_ok=True)
                
                # Write the decrypted content back to the original location
                with open(original_file_path, 'w', encoding='utf-8') as f:
                    f.write(decrypted_content)
                
                result['success'] = True
                result['unlocked_content'] = decrypted_content
                result['message'] = lock_config.get('unlock_message', f"⟡ {lock_name} unfolds...")
                result['restored_file'] = original_file_path
                
                print(f"⟡ File restored: {original_file_path}")
                
            except Exception as e:
                result['message'] = f"⧖ Failed to restore file: {e}"
                return result
        else:
            # Fallback to just showing content if no file path
            result['success'] = True
            result['unlocked_content'] = decrypted_content
            result['message'] = lock_config.get('unlock_message', f"⟡ {lock_name} unfolds...")
        
        return result
    
    def create_lock_file(self, lock_name: str, concept_file: str, glyph_sequences: List[str], 
                        question: str = "", unlock_message: str = "") -> bool:
        """Create a new lock file with multiple valid glyph sequences and delete original"""
        try:
            # Read the concept file to encrypt
            if not os.path.exists(concept_file):
                print(f"⧖ Concept file not found: {concept_file}")
                return False
            
            # Use first glyph sequence as encryption key
            primary_sequence = glyph_sequences[0]
            encrypted_content = self.encrypt_file(concept_file, primary_sequence)
            
            # Generate hashes for all valid sequences
            valid_hashes = [self.hash_glyph_sequence(seq) for seq in glyph_sequences]
            
            # Create lock configuration
            lock_config = {
                'concept_file': concept_file,
                'glyph_question': question or f"What sequence unlocks {lock_name}?",
                'valid_hashes': valid_hashes,
                'encrypted_content': encrypted_content,
                'unlock_message': unlock_message or f"⟡ {lock_name} unfolds..."
            }
            
            # Save lock file
            lock_path = self.locks_dir / f"{lock_name}.lock.yaml"
            with open(lock_path, 'w', encoding='utf-8') as file:
                yaml.dump(lock_config, file, default_flow_style=False, allow_unicode=True)
            
            # Delete the original file after successful lock creation
            os.remove(concept_file)
            print(f"⟡ Lock created: {lock_name}")
            print(f"⋇ Original file vanished: {concept_file}")
            return True
            
        except Exception as e:
            print(f"⧖ Error creating lock: {e}")
            return False
    
    def interactive_unlock_session(self):
        """Interactive session for attempting to unlock files"""
        print("⟡ Glyph Unlocker - Where symbols become keys")
        print("∴ Available locks:")
        
        locks = self.list_available_locks()
        if not locks:
            print("∅ No locks found. Create some first.")
            return
        
        for i, lock_name in enumerate(locks, 1):
            lock_config = self.load_lock_file(lock_name)
            question = lock_config.get('glyph_question', 'Unknown question') if lock_config else 'Error loading'
            print(f"  {i}. {lock_name}")
            print(f"     {question}")
        
        while True:
            try:
                print("\n⚘ Enter lock number to attempt (or 'exit' to quit):")
                choice = input("→ ").strip()
                
                if choice.lower() in ['exit', 'quit', 'q']:
                    print("∴ May the glyphs guide you...")
                    break
                
                try:
                    lock_index = int(choice) - 1
                    if 0 <= lock_index < len(locks):
                        lock_name = locks[lock_index]
                        self.attempt_single_unlock(lock_name)
                    else:
                        print("⧖ Invalid lock number")
                except ValueError:
                    print("⧖ Please enter a number or 'exit'")
                    
            except KeyboardInterrupt:
                print("\n∴ May the glyphs guide you...")
                break
    
    def attempt_single_unlock(self, lock_name: str):
        """Attempt to unlock a single file with user input"""
        lock_config = self.load_lock_file(lock_name)
        if not lock_config:
            print(f"⧖ Could not load lock: {lock_name}")
            return
        
        print(f"\n⟡ Attempting to unlock: {lock_name}")
        print(f"∴ {lock_config.get('glyph_question', 'What sequence unlocks this?')}")
        print("⚘ Enter your 3-glyph sequence:")
        
        glyph_sequence = input("→ ").strip()
        
        if not glyph_sequence:
            print("∅ Empty sequence")
            return
        
        print("↻ Testing sequence...")
        result = self.attempt_unlock(lock_name, glyph_sequence)
        
        print(f"\n{result['message']}")
        
        if result['success']:
            print("\n⟡ UNLOCKED CONTENT:")
            print("=" * 50)
            print(result['unlocked_content'])
            print("=" * 50)
        
        return result['success'] 