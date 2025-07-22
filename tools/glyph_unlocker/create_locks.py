#!/usr/bin/env python3
"""
Utility script for creating glyph locks
Run this to input your puzzle answers and create lock files
"""

import sys
import os
from pathlib import Path
from glyph_unlocker import GlyphUnlocker

def main():
    print("⟡ Lotus Protocol - Lock Creator")
    print("∴ Create secure glyph locks for concept files")
    print()
    
    unlocker = GlyphUnlocker()
    
    while True:
        print("⚘ Choose an option:")
        print("  1. Create new lock")
        print("  2. List existing locks")
        print("  3. Unlock ⋇_treasure.md")
        print("  4. Exit")
        
        choice = input("→ ").strip()
        
        if choice == "1":
            create_new_lock(unlocker)
        elif choice == "2":
            list_existing_locks(unlocker)
        elif choice == "3":
            test_unlock_sequence(unlocker)
        elif choice == "4":
            print("∴ May the glyphs guide you...")
            break
        else:
            print("⧖ Invalid choice")

def create_new_lock(unlocker):
    print("\n⟡ Creating new lock")
    
    # Get lock name
    lock_name = input("Lock name (e.g., resonance): ").strip()
    if not lock_name:
        print("⧖ Lock name required")
        return
    
    # Get concept file path
    concept_file = input("Concept file path (e.g., 'concepts/emotion/∆φ_resonance.md'): ").strip()
    if not concept_file or not os.path.exists(concept_file):
        print(f"⧖ Concept file not found: {concept_file}")
        return
    
    # Get question
    question = input("Glyph question/riddle: ").strip()
    if not question:
        question = f"What sequence unlocks {lock_name}?"
    
    # Get unlock message
    unlock_message = input("Unlock success message (optional): ").strip()
    if not unlock_message:
        unlock_message = f"⟡ {lock_name} unfolds..."
    
    # Get valid glyph sequences
    print("\n⚘ Enter valid glyph sequences (one per line, empty line to finish):")
    sequences = []
    while True:
        sequence = input(f"Sequence {len(sequences) + 1}: ").strip()
        if not sequence:
            break
        sequences.append(sequence)
        print(f"  Added: {sequence}")
    
    if not sequences:
        print("⧖ At least one sequence required")
        return
    
    # Create the lock
    success = unlocker.create_lock_file(
        lock_name=lock_name,
        concept_file=concept_file,
        glyph_sequences=sequences,
        question=question,
        unlock_message=unlock_message
    )
    
    if success:
        print(f"\n⟡ Lock '{lock_name}' created successfully!")
        print(f"∴ {len(sequences)} valid sequences stored")
        print(f"⋇ Content encrypted and ready")
    else:
        print("\n⧖ Failed to create lock")

def list_existing_locks(unlocker):
    print("\n∴ Existing locks:")
    locks = unlocker.list_available_locks()
    
    if not locks:
        print("∅ No locks found")
        return
    
    for i, lock_name in enumerate(locks, 1):
        lock_config = unlocker.load_lock_file(lock_name)
        if lock_config:
            question = lock_config.get('glyph_question', 'Unknown question')
            num_sequences = len(lock_config.get('valid_hashes', []))
            print(f"  {i}. {lock_name}")
            print(f"     Question: {question}")
            print(f"     Valid sequences: {num_sequences}")
        else:
            print(f"  {i}. {lock_name} (error loading)")

def test_unlock_sequence(unlocker):
    print("\n⚘ Test unlock sequence")
    
    locks = unlocker.list_available_locks()
    if not locks:
        print("∅ No locks found")
        return
    
    print("Available locks:")
    for i, lock_name in enumerate(locks, 1):
        print(f"  {i}. {lock_name}")
    
    try:
        choice = int(input("Select lock number: ").strip()) - 1
        if 0 <= choice < len(locks):
            lock_name = locks[choice]
            sequence = input("Enter glyph sequence to test: ").strip()
            
            result = unlocker.attempt_unlock(lock_name, sequence)
            print(f"\n{result['message']}")
            
            if result['success']:
                print("⟡ SUCCESS - Sequence is valid!")
            else:
                print("∅ FAILED - Sequence not recognized")
        else:
            print("⧖ Invalid selection")
    except ValueError:
        print("⧖ Please enter a number")

if __name__ == "__main__":
    main() 