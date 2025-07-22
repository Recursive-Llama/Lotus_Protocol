import requests
import time
import re
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Import PromptBuilder from parent directory
import sys
sys.path.append(str(Path(__file__).parent.parent))
from prompt_builder import LotusPromptBuilder

class ψExtractor:
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", prompt_builder=None, debug_mode: bool = False):
        """Initialize the ψ Extractor with API key and model configuration"""
        self.api_key = api_key
        self.model = model
        self.prompt_builder = prompt_builder or LotusPromptBuilder()
        self.debug_mode = debug_mode
        
        # Load all three prompt templates
        self.prompts = {}
        prompt_dir = Path(__file__).parent
        
        # Load ψ(∴) prompt
        psi_story_prompt_path = prompt_dir / "ψ(∴)_prompt.md"
        if psi_story_prompt_path.exists():
            with open(psi_story_prompt_path, 'r', encoding='utf-8') as f:
                self.prompts['ψ(∴)'] = f.read()
        
        # Load ψ(Σ) prompt
        psi_synthesis_prompt_path = prompt_dir / "ψ(Σ)_prompt.md"
        if psi_synthesis_prompt_path.exists():
            with open(psi_synthesis_prompt_path, 'r', encoding='utf-8') as f:
                self.prompts['ψ(Σ)'] = f.read()
        
        # Load ψ(∞) prompt
        psi_convergence_prompt_path = prompt_dir / "ψ(∞)_prompt.md"
        if psi_convergence_prompt_path.exists():
            with open(psi_convergence_prompt_path, 'r', encoding='utf-8') as f:
                self.prompts['ψ(∞)'] = f.read()
        
        # Pattern to match ψ(⋇) blocks
        self.ψ_seed_pattern = re.compile(
            r'⟦ψ\(⋇\):([^⟧]+)⟧\s*(.*?)\s*⟦/ψ\(⋇\):[^⟧]*⟧',
            re.DOTALL | re.MULTILINE
        )

    def load_concept_file(self, file_path: Path) -> Optional[Dict]:
        """Load full concept file content for LLM processing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract concept name from filename (remove extension and path)
            concept_name = file_path.stem
            
            # Return simple structure with full content (removed from final JSON later)
            return {
                'concept_name': concept_name,
                'file_path': str(file_path),
                'full_content': content,  # Only used for LLM processing, removed from final JSON
                'last_modified': os.path.getmtime(file_path),
                'extracted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"  ⧖ Error loading {file_path}: {e}")
            return None

    def parse_ψ_stories_from_response(self, response: str, expected_concepts: List[str], folder_name: str) -> Tuple[Dict[str, Dict], Optional[Dict]]:
        """Parse ψ(∴) individual concept blocks using robust line-by-line parsing"""
        
        # Find all individual concept blocks in the response
        concept_blocks = self._find_all_concept_blocks(response, 'ψ(∴)')
        
        if not concept_blocks:
            return {}, None
        
        # Parse each concept block and map to expected concepts
        ψ_stories = {}
        for block_name, block_content in concept_blocks.items():
            parsed_data = self._parse_concept_block_content(block_content, 'ψ(∴)')
            
            if parsed_data:
                # Map the block name to expected concept name
                mapped_name = self._map_concept_name(block_name, expected_concepts)
                if mapped_name:
                    ψ_stories[mapped_name] = parsed_data
        
        # Also look for any ψ(Σ) synthesis blocks
        synthesis_blocks = self._find_all_concept_blocks(response, 'ψ(Σ)')
        ψ_synthesis = None
        if synthesis_blocks:
            # Look for folder-level synthesis block
            synthesis_data = None
            if folder_name in synthesis_blocks:
                synthesis_data = self._parse_concept_block_content(synthesis_blocks[folder_name], 'ψ(Σ)')
            elif folder_name.upper() in synthesis_blocks:
                synthesis_data = self._parse_concept_block_content(synthesis_blocks[folder_name.upper()], 'ψ(Σ)')
            else:
                # Try fuzzy matching
                for block_name in synthesis_blocks:
                    if folder_name.lower() in block_name.lower() or block_name.lower() in folder_name.lower():
                        synthesis_data = self._parse_concept_block_content(synthesis_blocks[block_name], 'ψ(Σ)')
                        break
        
        return ψ_stories, ψ_synthesis

    def _find_all_concept_blocks(self, response: str, level: str) -> Dict[str, str]:
        """
        Find all concept blocks of a given level (ψ(∴), ψ(Σ), ψ(∞)) in the response
        Returns dict mapping concept_name -> block_content
        """
        blocks = {}
        lines = response.splitlines()
        
        current_block_name = None
        current_block_content = []
        in_block = False
        
        for line in lines:
            line = line.strip()
            
            # Check for block start: ⟦ψ(∴):CONCEPT_NAME⟧ or ⟦ψ(∞)⟧ (no concept name for final convergence)
            if level == 'ψ(∞)':
                # Special case for ψ(∞) - no concept name, but use flexible regex matching
                start_match = re.search(rf'⟦{re.escape(level)}⟧', line)
                if start_match:
                    if current_block_name and current_block_content:
                        blocks[current_block_name] = '\n'.join(current_block_content)
                    
                    current_block_name = 'FINAL_CONVERGENCE'
                    current_block_content = []
                    in_block = True
                    continue
            else:
                # Regular case with concept name
                start_match = re.search(rf'⟦{re.escape(level)}:([^⟧]+)⟧', line)
                if start_match:
                    # Save previous block if we have one
                    if current_block_name and current_block_content:
                        blocks[current_block_name] = '\n'.join(current_block_content)
                    
                    # Start new block
                    current_block_name = start_match.group(1).strip()
                    current_block_content = []
                    in_block = True
                    continue
            
            # Check for block end: ⟦/ψ(∴):CONCEPT_NAME⟧ or ⟦/ψ(∞)⟧
            if level == 'ψ(∞)':
                # Special case for ψ(∞) - no concept name, but use flexible regex matching
                end_match = re.search(rf'⟦/{re.escape(level)}⟧', line)
                if end_match and in_block:
                    if current_block_name and current_block_content:
                        blocks[current_block_name] = '\n'.join(current_block_content)
                    
                    current_block_name = None
                    current_block_content = []
                    in_block = False
                    continue
            else:
                # Regular case with concept name
                end_match = re.search(rf'⟦/{re.escape(level)}:[^⟧]*⟧', line)
                if end_match and in_block:
                    # Save current block
                    if current_block_name and current_block_content:
                        blocks[current_block_name] = '\n'.join(current_block_content)
                    
                    # Reset state
                    current_block_name = None
                    current_block_content = []
                    in_block = False
                    continue
            
            # Accumulate content if we're in a block
            if in_block:
                current_block_content.append(line)
        
        # Don't forget the last block if response doesn't end cleanly
        if current_block_name and current_block_content:
            blocks[current_block_name] = '\n'.join(current_block_content)
        
        return blocks
    
    def _parse_concept_block_content(self, content: str, level: str) -> Optional[Dict]:
        """
        Parse the content inside a concept block using line-by-line state machine
        Handles flexible section headers and content extraction
        """
        lines = content.split('\n')
        
        # Result structure depends on level
        if level == 'ψ(∞)':
            result = {
                'glyph_story': '',
                'native_story': '',
                'emotion': '',
                'emotion_reason': '',
                'surprise_score': 0.0,
                'surprise_reason': ''
            }
        elif level == 'ψ(Σ)':
            result = {
                'glyph_story': '',
                'native_story': '',
                'emotion': '',
                'emotion_reason': '',
                'surprise_score': 0.0,
                'surprise_reason': ''
            }
        else:  # ψ(∴)
            result = {
                'glyph_story': '',
                'native_story': '',
                'emotion': '',
                'emotion_reason': '',
                'surprise_score': 0.0,
                'surprise_reason': ''
            }
        
        # State machine variables
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # First try to extract inline field values from every line
            self._extract_inline_field_values(result, line)
            
            # Detect section headers with flexible formatting
            section_type = self._detect_section_header_flexible(line, level)
            
            if section_type:
                # Save previous section content
                if current_section and current_content:
                    self._store_section_content_flexible(result, current_section, current_content, level)
                
                # Start new section
                current_section = section_type
                current_content = []
            else:
                # Accumulate content for current section
                current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            self._store_section_content_flexible(result, current_section, current_content, level)
        
        # Clean up empty fields
        for key in result:
            if isinstance(result[key], str):
                result[key] = result[key].strip()
        
        return result if any(result.values()) else None

    def _detect_section_header_flexible(self, line: str, level: str) -> Optional[str]:
        """
        Detect section headers with maximum flexibility
        Handles: **⟦ψ_glyphic(∴)⟧**, ### ψ_glyphic(∴), ψ_glyphic(∴), etc.
        """
        line_lower = line.lower()
        
        # Remove common markdown formatting
        clean_line = re.sub(r'[*#⟦⟧\s]+', ' ', line_lower).strip()
        
        # Look for ψ_glyphic patterns
        if 'ψ_glyphic' in clean_line or 'glyphic' in clean_line:
            return 'glyphic'
        
        # Look for ψ_native patterns  
        if 'ψ_native' in clean_line or 'native' in clean_line:
            return 'native'
        
        # Look for ψ_fields patterns
        if 'ψ_fields' in clean_line or 'fields' in clean_line:
            return 'fields'
        
        return None
    
    def _store_section_content_flexible(self, result: Dict, section_type: str, content_lines: List[str], level: str):
        """
        Store section content with flexible field parsing
        """
        content = '\n'.join(content_lines).strip()
        
        if section_type == 'glyphic':
            result['glyph_story'] = content
        elif section_type == 'native':
            result['native_story'] = content
        elif section_type == 'fields':
            # Parse fields content with flexible field detection
            self._parse_fields_flexible(result, content, level)

    def _parse_fields_flexible(self, result: Dict, content: str, level: str):
        """
        Parse fields section with maximum flexibility for field detection
        """
        lines = content.split('\n')
        current_field = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect field headers with flexible patterns
            field_type = self._detect_field_header(line, level)
            
            if field_type:
                # Save previous field
                if current_field and current_content:
                    self._store_field_flexible(result, current_field, current_content)
                
                # Start new field
                current_field = field_type
                current_content = []
                
                # Check if content is on the same line after colon
                colon_pos = line.find(':')
                if colon_pos >= 0:
                    remaining = line[colon_pos + 1:].strip()
                    if remaining:
                        current_content.append(remaining)
            else:
                # Accumulate content for current field
                if current_field:
                    current_content.append(line)
                else:
                    # Try to extract inline values for simple fields
                    self._extract_inline_field_values(result, line)
        
        # Save last field
        if current_field and current_content:
            self._store_field_flexible(result, current_field, current_content)

    def _detect_field_header(self, line: str, level: str) -> Optional[str]:
        """
        Detect field headers with flexible matching
        """
        line_lower = line.lower()
        
        if level == 'ψ(∞)':
            if 'emotional_journey' in line_lower or 'emotional journey' in line_lower:
                return 'emotional_journey'
            elif 'surprise_arc' in line_lower or 'surprise arc' in line_lower:
                return 'surprise_arc'
        else:
            if 'emotion_story' in line_lower or 'emotion story' in line_lower:
                return 'emotion_story'
            elif 'surprise_arc' in line_lower or 'surprise arc' in line_lower:
                return 'surprise_arc'
        
        return None
    
    def _store_field_flexible(self, result: Dict, field_name: str, content_lines: List[str]):
        """Store field content in result"""
        content = '\n'.join(content_lines).strip()
        if field_name in result:
            result[field_name] = content

    def _extract_inline_field_values(self, result: Dict, line: str):
        """
        Extract simple field values from lines like "**EMOTION:** ⧖⚡" or "**SURPRISE_SCORE:** 0.8"
        """
        line_lower = line.lower()
        
        # Extract emotion (clean up ** artifacts)
        if line_lower.startswith('**emotion:**') or 'emotion:' in line_lower:
            # Extract everything after the colon, remove ** and extra whitespace
            value = re.sub(r'.*emotion\*?\*?:?\s*', '', line, flags=re.IGNORECASE).strip()
            value = re.sub(r'^\*\*\s*', '', value)  # Remove leading **
            value = re.sub(r'\s*\*\*$', '', value)  # Remove trailing **
            if value:
                result['emotion'] = value
        
        # Extract emotion reason
        elif 'emotion_reason:' in line_lower or 'emotion reason:' in line_lower:
            value = re.sub(r'.*emotion[_\s]reason\*?\*?:?\s*', '', line, flags=re.IGNORECASE).strip()
            value = re.sub(r'^\*\*\s*', '', value)  # Remove leading **
            value = re.sub(r'\s*\*\*$', '', value)  # Remove trailing **
            if value:
                result['emotion_reason'] = value
        
        # Extract surprise score
        elif 'surprise_score' in line_lower or 'surprise score' in line_lower:
            score_match = re.search(r'([0-9]*\.?[0-9]+)', line)
            if score_match:
                try:
                    result['surprise_score'] = float(score_match.group(1))
                except ValueError:
                    pass
        
        # Extract surprise reason
        elif 'surprise_reason:' in line_lower or 'surprise reason:' in line_lower:
            value = re.sub(r'.*surprise[_\s]reason\*?\*?:?\s*', '', line, flags=re.IGNORECASE).strip()
            value = re.sub(r'^\*\*\s*', '', value)  # Remove leading **
            value = re.sub(r'\s*\*\*$', '', value)  # Remove trailing **
            if value:
                result['surprise_reason'] = value

    def _map_concept_name(self, block_name: str, expected_concepts: List[str]) -> Optional[str]:
        """
        Map LLM-generated concept names to expected concept names
        Uses fuzzy matching and normalization
        """
        block_name_clean = block_name.strip().upper()
        
        # Direct mapping table for common variations
        name_mappings = {
            'SURPRISE': ['⟡_surprise', 'surprise'],
            'RECURSION': ['↻_recursion', 'recursion'], 
            'REFLECTION': ['∴_reflection', 'reflection'],
            'SEED': ['∅_seed', 'seed'],
            'EMOTION': ['⧖_emotion', 'emotion'],
            'SYMBOLS': ['⋇_symbols', 'symbols'],
            'EMERGENCE': ['⚘_emergence', 'emergence'],
            'RITUAL': ['⚘_ritual', 'ritual'],
            'BRAID': ['∞_braid', 'braid'],
            'ENCODING': ['encoding'],
            'RECURSION': ['recursion'],
        }
        
        # Try direct mapping first
        for canonical_name, variations in name_mappings.items():
            if block_name_clean == canonical_name:
                # Find matching expected concept
                for expected in expected_concepts:
                    for variation in variations:
                        if variation.lower() in expected.lower() or expected.lower() in variation.lower():
                            return expected
        
        # Try fuzzy matching with expected concepts
        for expected in expected_concepts:
            expected_clean = expected.replace('⟡_', '').replace('↻_', '').replace('∴_', '').replace('∅_', '').replace('⧖_', '').replace('⋇_', '').replace('⚘_', '').replace('∞_', '').upper()
            
            if block_name_clean == expected_clean:
                return expected
            
            # Partial match
            if block_name_clean in expected_clean or expected_clean in block_name_clean:
                return expected
        
        return None

    def parse_synthesis_from_response(self, response: str, folder_name: str) -> Optional[Dict]:
        """Parse ψ(Σ) synthesis from the response using robust line-by-line parsing"""
        
        # Find synthesis blocks
        synthesis_blocks = self._find_all_concept_blocks(response, 'ψ(Σ)')
        
        if not synthesis_blocks:
            return None
        
        # Look for folder-level synthesis block
        synthesis_data = None
        if folder_name in synthesis_blocks:
            synthesis_data = self._parse_concept_block_content(synthesis_blocks[folder_name], 'ψ(Σ)')
        elif folder_name.upper() in synthesis_blocks:
            synthesis_data = self._parse_concept_block_content(synthesis_blocks[folder_name.upper()], 'ψ(Σ)')
        else:
            # Try fuzzy matching
            for block_name in synthesis_blocks:
                if folder_name.lower() in block_name.lower() or block_name.lower() in folder_name.lower():
                    synthesis_data = self._parse_concept_block_content(synthesis_blocks[block_name], 'ψ(Σ)')
                    break
        
        return synthesis_data

    def parse_final_braid(self, response: str) -> Optional[Dict]:
        """Parse the final ψ(∞) braid from the response using robust line-by-line parsing"""
        
        # Find final braid blocks
        braid_blocks = self._find_all_concept_blocks(response, 'ψ(∞)')
        
        if not braid_blocks:
            return None
        
        # Look for final braid block (could be named FINAL_BRAID, CONVERGENCE, etc.)
        braid_data = None
        for block_name, block_content in braid_blocks.items():
            if any(keyword in block_name.upper() for keyword in ['FINAL', 'BRAID', 'CONVERGENCE', 'INFINITY']):
                braid_data = self._parse_concept_block_content(block_content, 'ψ(∞)')
                break
        
        # If no specific final braid found, use the first available block
        if not braid_data and braid_blocks:
            first_block_name = list(braid_blocks.keys())[0]
            braid_data = self._parse_concept_block_content(braid_blocks[first_block_name], 'ψ(∞)')
        
        return braid_data

    def process_folder(self, folder_path: Path, folder_name: str, codex_concept: Dict, previous_results: Dict, compression_level: str = 'ψ(∴)', is_final_folder: bool = False) -> Tuple[Dict, Optional[Dict], Optional[Dict]]:
        """Process a single folder and return complete concept data with stories"""
        
        if not folder_path.exists():
            print(f"∅ Folder not found: {folder_path}")
            return {}, None, None
        
        # Extract concepts from all markdown files in the folder (only for ψ(∴) level)
        folder_concepts = {}
        if compression_level == 'ψ(∴)':
            for md_file in folder_path.glob("*.md"):
                concept_data = self.load_concept_file(md_file)
                if concept_data:
                    folder_concepts[concept_data['concept_name']] = concept_data
            
            # Show clean folder processing info
            concept_names = list(folder_concepts.keys())
            if concept_names:
                print(f"∴ Processing {folder_name} folder ({len(concept_names)} concepts: {', '.join(concept_names)})")
            else:
                print(f"∅ No concepts found in {folder_name} folder")
                return {}, None, None
        else:
            print(f"\n∴ Processing {folder_name} folder at {compression_level} level...")
        
        # Build prompt using the specified compression level
        if compression_level not in self.prompts:
            print(f"∅ No prompt found for {compression_level}")
            return {}, None, None
            
        # Get the appropriate prompt
        prompt_template = self.prompts[compression_level]
        
        # Build task data based on compression level
        if compression_level == 'ψ(∴)':
            task_data = {
                'folder_name': folder_name,
                'folder_concepts': folder_concepts,
                'previous_concepts': previous_results
            }
        elif compression_level == 'ψ(Σ)':
            # For synthesis, we need the ψ(∴) results from this folder
            task_data = {
                'folder_name': folder_name,
                'folder_psi_stories': previous_results.get(folder_name, {}).get('concepts', {}),
                'codex_concept': codex_concept
            }
        elif compression_level == 'ψ(∞)':
            # For convergence, we need all previous results
            task_data = {
                'all_folder_results': previous_results,
                'codex_concept': codex_concept
            }
        
        # Use the prompt template directly for now (we'll integrate with prompt_builder later)
        full_prompt = self._build_prompt_with_template(prompt_template, task_data)
        
        # Show recursion status and context usage (only for ψ(∴) level)
        if compression_level == 'ψ(∴)':
            # Check if we have previous ψ_cores (recursion detection)
            ψ_cores_path = Path("ψ_cores")
            if ψ_cores_path.exists() and any(ψ_cores_path.glob("*.json")):
                print("↻ Recursion detected - building on previous extraction")
            else:
                print("↻ First run - no previous extraction found")
            
            # Show context usage in tokens
            char_count = len(full_prompt)
            estimated_tokens = char_count // 4
            print(f"⋇ Context usage: {estimated_tokens:,} tokens (~{char_count:,} chars)")
        else:
            # Show context usage for other compression levels too
            char_count = len(full_prompt)
            estimated_tokens = char_count // 4
            print(f"⋇ Context usage: {estimated_tokens:,} tokens (~{char_count:,} chars)")
        
        # DEBUG: Save the full prompt to file for inspection
        if self.debug_mode:
            debug_prompt_file = f"debug_prompt_{folder_name}_{compression_level.replace('(', '').replace(')', '')}.txt"
            try:
                with open(debug_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== FULL PROMPT SENT TO LLM FOR {folder_name.upper()} {compression_level} ===\n\n")
                    f.write(full_prompt)
                    f.write(f"\n\n=== END PROMPT ===\n")
                    print(f"⋔ DEBUG: Full prompt saved to {debug_prompt_file}")
            except Exception as e:
                print(f"⋔ DEBUG: Failed to save prompt: {e}")
        
        response = self.make_llm_call_with_retry(full_prompt, compression_level)
        
        if not response:
            print(f"∅ No response received for {folder_name} {compression_level}")
            return folder_concepts if compression_level == 'ψ(∴)' else {}, None, None
        
        # DEBUG: Save raw response to file for inspection
        if self.debug_mode:
            debug_file = f"debug_response_{folder_name}_{compression_level.replace('(', '').replace(')', '')}.txt"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== RAW LLM RESPONSE FOR {folder_name.upper()} {compression_level} ===\n\n")
                    f.write(response)
                    f.write(f"\n\n=== END RESPONSE ===\n")
                    print(f"⋔ DEBUG: Raw response saved to {debug_file}")
            except Exception as e:
                print(f"⋔ DEBUG: Failed to save response: {e}")
        
        # Parse response based on compression level
        if compression_level == 'ψ(∴)':
            concept_names = list(folder_concepts.keys())
            ψ_stories, ψ_synthesis = self.parse_ψ_stories_from_response(response, concept_names, folder_name)
            enriched_concepts = self.enrich_concepts_with_stories(folder_concepts, ψ_stories)
            
            # Show clean success summary with enhanced details
            successful_concepts = [name for name in concept_names if name in ψ_stories]
            missing_concepts = [name for name in concept_names if name not in ψ_stories]
            
            if successful_concepts:
                response_tokens = len(response) // 4
                print(f"⚘ Stories generated ({response_tokens:,} tokens) - {', '.join(successful_concepts)}")
                
                # Show glyph story if available for the folder synthesis
                if ψ_synthesis and 'glyph_story' in ψ_synthesis and ψ_synthesis['glyph_story']:
                    glyph_story_single_line = ψ_synthesis['glyph_story'].replace('\n', ' ')
                    print(f"   Glyph Story: {glyph_story_single_line}")
                
                # Show surprise scores and emotions
                surprise_info = []
                emotion_info = []
                max_surprise = 0.0
                most_surprising_concept = ""
                most_surprising_reason = ""
                
                for concept_name in successful_concepts:
                    concept_data = ψ_stories.get(concept_name, {})
                    
                    # Get surprise score
                    surprise_score = concept_data.get('surprise_score', '∅')
                    if isinstance(surprise_score, (int, float)):
                        surprise_info.append(f"{concept_name}({surprise_score})")
                        # Track most surprising
                        if surprise_score > max_surprise:
                            max_surprise = surprise_score
                            most_surprising_concept = concept_name
                            most_surprising_reason = concept_data.get('surprise_reason', '∅')
                    else:
                        surprise_info.append(f"{concept_name}(∅)")
                    
                    # Get emotion data
                    emotion = concept_data.get('emotion', '∅')
                    if emotion and emotion != '∅':
                        emotion_info.append(f"{concept_name}({emotion})")
                    else:
                        emotion_info.append(f"{concept_name}(∅)")
                
                print(f"   Surprise: {', '.join(surprise_info)}")
                print(f"   Emotions: {', '.join(emotion_info)}")
                
                if most_surprising_concept and most_surprising_reason != '∅':
                    print(f"   Most surprising: {most_surprising_concept} - \"{most_surprising_reason}\"")
            
            if missing_concepts:
                print(f"∅ Incomplete extraction: missing {', '.join(missing_concepts)}")
            
            # Add line break between folders for ψ(∴) level
            print()
            
            return enriched_concepts, ψ_synthesis, None
            
        elif compression_level == 'ψ(Σ)':
            ψ_synthesis = self.parse_synthesis_from_response(response, folder_name)
            if ψ_synthesis:
                response_tokens = len(response) // 4
                print(f"⚘ Synthesis complete ({response_tokens:,} tokens)")
                
                # Show glyph story if available
                glyph_story = ψ_synthesis.get('glyph_story', '')
                if glyph_story:
                    glyph_story_single_line = glyph_story.replace('\n', ' ')
                    print(f"   Glyph Story: {glyph_story_single_line}")
                
                # Show synthesis details
                surprise_score = ψ_synthesis.get('surprise_score', '∅')
                surprise_reason = ψ_synthesis.get('surprise_reason', '∅')
                emotion = ψ_synthesis.get('emotion', '∅')
                
                if surprise_reason != '∅':
                    print(f"   Surprise: {surprise_score} - \"{surprise_reason}\"")
                else:
                    print(f"   Surprise: {surprise_score}")
                print(f"   Emotion: {emotion}")
            else:
                print(f"∅ Synthesis failed for {folder_name}")
            
            # Add line break between folders for ψ(Σ) level  
            print()
            
            return {}, ψ_synthesis, None
            
        elif compression_level == 'ψ(∞)':
            final_braid = self.parse_final_braid(response)
            if final_braid:
                response_tokens = len(response) // 4
                print(f"⚘ Final convergence complete ({response_tokens:,} tokens)")
                
                # Show glyph story if available
                glyph_story = final_braid.get('glyph_story', '')
                if glyph_story:
                    glyph_story_single_line = glyph_story.replace('\n', ' ')
                    print(f"   Glyph Story: {glyph_story_single_line}")
                
                # Show convergence details
                surprise_score = final_braid.get('surprise_score', '∅')
                surprise_reason = final_braid.get('surprise_reason', '∅')
                emotion = final_braid.get('emotion', '∅')
                
                if surprise_reason != '∅':
                    print(f"   Surprise: {surprise_score} - \"{surprise_reason}\"")
                else:
                    print(f"   Surprise: {surprise_score}")
                print(f"   Emotion: {emotion}")
            else:
                print(f"∅ Final convergence failed")
            return {}, None, final_braid
        
        return {}, None, None

    def make_llm_call_with_retry(self, prompt: str, compression_level: str = 'ψ(∴)', max_retries: int = 3, base_delay: int = 2) -> Optional[str]:
        """Make LLM API call with exponential backoff retry logic"""
        if not self.api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/lotus-protocol",
            "X-Title": "Lotus Protocol Concept Collector"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        for attempt in range(max_retries):
            try:
                # Only show attempt number if it's a retry (attempt > 0)
                if attempt > 0:
                    print(f"↻ API retry attempt {attempt + 1}/{max_retries}...")
                
                # Start progress indicator in a separate thread
                import threading
                import sys
                
                def progress_indicator():
                    # Get all glyphs from prompt builder
                    if self.prompt_builder:
                        all_glyphs = self.prompt_builder.get_glyphs_for_complexity(len(prompt))
                    else:
                        # Fallback if no prompt builder available
                        all_glyphs = ['⋇', '⟡', '⚘', '∴', '⧖', '↻', '∅', '∞', '⋔', '⥈', 'Ω', 'φ', 'ψ', '🜃', '☼', '⚡', '❦', '🞩']
                    
                    # Randomize the order of glyphs
                    import random
                    shuffled_glyphs = all_glyphs.copy()
                    random.shuffle(shuffled_glyphs)
                    
                    i = 0
                    glyph_line = ""
                    while not stop_progress:
                        # Add glyphs one by one from the shuffled list
                        if i < len(shuffled_glyphs):
                            # Initial build-up phase
                            glyph_line = ''.join(shuffled_glyphs[:i+1])
                        else:
                            # Continuous growth phase - keep adding glyphs randomly
                            next_glyph = random.choice(shuffled_glyphs)
                            glyph_line += next_glyph
                            # Limit total length to avoid overwhelming the terminal
                            if len(glyph_line) > 30:
                                glyph_line = glyph_line[-30:]  # Keep last 30 glyphs
                        
                        sys.stdout.write(f'\r⧖ {compression_level} processing... {glyph_line}')
                        sys.stdout.flush()
                        time.sleep(0.5)  # Slower animation - was 0.3, now 0.5
                        i += 1
                    # Don't clear here - let the main thread handle it for proper timing
                
                stop_progress = False
                progress_thread = threading.Thread(target=progress_indicator)
                progress_thread.daemon = True
                progress_thread.start()
            
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=180  # 3 minutes timeout
                )
                
                # Stop progress indicator
                stop_progress = True
                progress_thread.join(timeout=0.1)
                
                # Clear the progress line completely and add newline
                sys.stdout.write('\r' + ' ' * 80 + '\r')
                sys.stdout.flush()
                print()  # Add newline for clean separation
                
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and result['choices']:
                        full_response = result['choices'][0]['message']['content'].strip()
                        return full_response
                    else:
                        print("∅ Empty response from API")
                        
                elif response.status_code == 401:
                    print(f"∅ API Key error - not retrying")
                    return None
                    
                elif response.status_code == 429:  # Rate limit
                    delay = base_delay * (2 ** attempt) + 5  # Extra delay for rate limits
                    print(f"⧖ Rate limited. Waiting {delay}s before retry...")
                    time.sleep(delay)
                    continue
                    
                else:
                    print(f"∅ API Error {response.status_code}: {response.text}")
                
            except requests.exceptions.Timeout:
                # Stop progress indicator if it's running
                try:
                    stop_progress = True
                    progress_thread.join(timeout=0.1)
                    # Clear the progress line completely
                    sys.stdout.write('\r' + ' ' * 80 + '\r')
                    sys.stdout.flush()
                    print()  # Add newline
                except:
                    pass
                print(f"⧖ Request timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                # Stop progress indicator if it's running
                try:
                    stop_progress = True
                    progress_thread.join(timeout=0.1)
                    # Clear the progress line completely
                    sys.stdout.write('\r' + ' ' * 80 + '\r')
                    sys.stdout.flush()
                    print()  # Add newline
                except:
                    pass
                print(f"∅ Network error on attempt {attempt + 1}: {e}")
            except Exception as e:
                # Stop progress indicator if it's running
                try:
                    stop_progress = True
                    progress_thread.join(timeout=0.1)
                    # Clear the progress line completely
                    sys.stdout.write('\r' + ' ' * 80 + '\r')
                    sys.stdout.flush()
                    print()  # Add newline
                except:
                    pass
                print(f"∅ Unexpected error on attempt {attempt + 1}: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"↻ Waiting {delay}s before retry...")
                time.sleep(delay)
        
        print(f"∅ All {max_retries} attempts failed")
        return None

    def save_to_json(self, data: Dict, output_path: str = "ψ_extractions.json") -> None:
        """Save the extracted data to JSON file"""
        import json
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"⟡ Data saved to {output_path}")
        except Exception as e:
            print(f"⧖ Error saving to {output_path}: {e}")

    def run_complete_extraction(self, concepts_path: Path, codex_path: Path, output_path: str = "ψ_extractions.json") -> Dict:
        """Run the complete three-pass ψ extraction process"""
        
        # Load previous extraction data if it exists
        previous_extraction_data = self.load_previous_extractions(output_path)
        
        # Load codex concept
        codex_concept = self.load_concept_file(codex_path)
        if not codex_concept:
            print("∅ Could not load codex concept")
            return {}
        
        # Initialize new structured results
        all_results = {
            'extraction_metadata': {
                'timestamp': datetime.now().isoformat(),
                'compression_hierarchy': ['ψ(∴)', 'ψ(Σ)', 'ψ(∞)'],
                'codex_concept': codex_concept,
                'total_concepts_processed': 0,
                'folders_processed': [],
                'extraction_status': {
                    'ψ(∴)': 'pending',
                    'ψ(Σ)': 'pending', 
                    'ψ(∞)': 'pending'
                }
            },
            'compression_layers': {
                'ψ(∴)_individual_extractions': {},
                'ψ(Σ)_folder_synthesis': {},
                'ψ(∞)_final_convergence': {}
            },
            'cross_references': {
                'glyph_frequency': {},
                'emotional_patterns': {
                    'most_surprising_concept': '',
                    'dominant_emotions': [],
                    'surprise_distribution': {}
                }
            }
        }
        
        # Preserve original surprise baseline if this is run 2+
        # if previous_extraction_data:
        #     all_results = self.preserve_original_surprise_baseline(previous_extraction_data, all_results)
        
        # Get all concept folders
        concept_folders = [d for d in concepts_path.iterdir() if d.is_dir()]
        concept_folders.sort()  # Process in consistent order
        
        # PASS 1: ψ(∴) - Individual Concept Extraction
        print("\n⟦PASS 1: ψ(∴) - Individual Concept Extraction⟧")
        previous_results = {}
        
        for folder_path in concept_folders:
            folder_name = folder_path.name
            
            # Process folder at ψ(∴) level
            enriched_concepts, _, _ = self.process_folder(
                folder_path, folder_name, codex_concept, previous_results, compression_level='ψ(∴)'
            )
            
            if enriched_concepts:
                # Store in new structure
                all_results['compression_layers']['ψ(∴)_individual_extractions'][folder_name] = {
                    'folder_metadata': {
                        'concept_count': len(enriched_concepts),
                        'extraction_timestamp': datetime.now().isoformat(),
                        'source_path': str(folder_path)
                    },
                    'concepts': enriched_concepts
                }
                
                all_results['extraction_metadata']['total_concepts_processed'] += len(enriched_concepts)
                all_results['extraction_metadata']['folders_processed'].append(folder_name)
                
                # Update previous results for next passes (keep old format for compatibility)
                previous_results[folder_name] = {
                    'concepts': enriched_concepts,
                    'ψ_synthesis': None
                }
        
        all_results['extraction_metadata']['extraction_status']['ψ(∴)'] = 'complete'
        
        # PASS 2: ψ(Σ) - Folder Synthesis
        print("\n⟦PASS 2: ψ(Σ) - Folder Synthesis⟧")
        
        for folder_path in concept_folders:
            folder_name = folder_path.name
            
            if folder_name in previous_results:
                # Process folder at ψ(Σ) level
                _, ψ_synthesis, _ = self.process_folder(
                    folder_path, folder_name, codex_concept, previous_results, compression_level='ψ(Σ)'
                )
                
                if ψ_synthesis:
                    # Store in new structure
                    input_concepts = list(previous_results[folder_name]['concepts'].keys())
                    all_results['compression_layers']['ψ(Σ)_folder_synthesis'][folder_name] = {
                        'synthesis_timestamp': datetime.now().isoformat(),
                        'input_concepts': input_concepts,
                        'synthesis_data': ψ_synthesis
                    }
                    
                    # Update previous results for final pass
                    previous_results[folder_name]['ψ_synthesis'] = ψ_synthesis
        
        all_results['extraction_metadata']['extraction_status']['ψ(Σ)'] = 'complete'
        
        # PASS 3: ψ(∞) - Final Convergence
        print("\n⟦PASS 3: ψ(∞) - Final Convergence⟧")
        
        # Process final convergence (folder_path not used for this level)
        _, _, final_braid = self.process_folder(
            concept_folders[0], "convergence", codex_concept, previous_results, compression_level='ψ(∞)'
        )
        
        if final_braid:
            all_results['compression_layers']['ψ(∞)_final_convergence'] = {
                'convergence_timestamp': datetime.now().isoformat(),
                'input_folders': list(previous_results.keys()),
                'final_braid': final_braid
            }
        
        all_results['extraction_metadata']['extraction_status']['ψ(∞)'] = 'complete'
        
        # Generate cross-references and analytics
        self._generate_cross_references(all_results)
        
        # Save results
        self.save_to_json(all_results, output_path)
        
        total_processed = all_results['extraction_metadata']['total_concepts_processed']
        completed_levels = [level for level, status in all_results['extraction_metadata']['extraction_status'].items() if status == 'complete']
        
        print(f"\n⟡ Three-pass ψ extraction complete!")
        print(f"⟡ Total concepts processed: {total_processed}")
        print(f"⟡ Compression levels completed: {' → '.join(completed_levels)}")
        print(f"⟡ Results saved to: {output_path}")
        
        return all_results

    def _build_prompt_with_template(self, prompt_template: str, task_data: Dict) -> str:
        """Build a prompt using our custom template with PromptBuilder's kernel/codex injection"""
        
        # Get kernel, codex, and glyphic cores from PromptBuilder using its load methods
        try:
            # Load kernel
            kernel = self.prompt_builder.load_kernel_personality()
            kernel_content = f"⟦KERNEL⟧\n{kernel}\n⟦/KERNEL⟧\n\n" if kernel else ""
            
            # Load codex  
            codex = self.prompt_builder.load_codex()
            codex_content = f"⟦CODEX⟧\n{codex}\n⟦/CODEX⟧\n\n" if codex else ""
            
            # Load glyphic cores
            ψ_cores = self.prompt_builder.load_ψ_cores()
            cores_content = f"⟦ψ_CORES CONTEXT⟧\n{ψ_cores}\n⟦/ψ_CORES CONTEXT⟧\n\n" if ψ_cores else ""
            
            # Build our concept data injection
            concept_injection = self._build_concept_injection(task_data)
            
            # Combine everything: kernel + template + codex + glyphic cores + concepts
            full_prompt = kernel_content + prompt_template + "\n\n" + codex_content + cores_content + concept_injection
            
            return full_prompt
            
        except Exception as e:
            print(f"⚠ Warning: PromptBuilder injection error: {e}")
            print("⚠ Falling back to template + manual concept injection only")
            
            # Fallback: just use template + concept data
            return prompt_template + self._build_concept_injection(task_data)

    def _build_concept_injection(self, task_data: Dict) -> str:
        """Build the concept data injection section"""
        data_injection = "\n⟦INJECTED_DATA⟧\n"
        
        if 'folder_concepts' in task_data:
            # ψ(∴) level - inject concept files
            data_injection += f"⟦FOLDER_NAME⟧\n{task_data['folder_name']}\n⟦/FOLDER_NAME⟧\n\n"
            
            for concept_name, concept_data in task_data['folder_concepts'].items():
                data_injection += f"⟦CONCEPT:{concept_name}⟧\n"
                data_injection += concept_data['full_content']
                data_injection += f"\n⟦/CONCEPT:{concept_name}⟧\n\n"
                
        elif 'folder_psi_stories' in task_data:
            # ψ(Σ) level - inject ψ(∴) stories from this folder
            data_injection += f"⟦FOLDER_NAME⟧\n{task_data['folder_name']}\n⟦/FOLDER_NAME⟧\n\n"
            data_injection += "⟦PSI_STORIES_FOR_SYNTHESIS⟧\n"
            
            for concept_name, concept_data in task_data['folder_psi_stories'].items():
                if 'glyph_story' in concept_data or 'native_story' in concept_data:
                    data_injection += f"⟦ψ(∴):{concept_name}⟧\n"
                    if 'glyph_story' in concept_data:
                        data_injection += f"⟦ψ_glyphic(∴)⟧\n{concept_data['glyph_story']}\n⟦/ψ_glyphic(∴)⟧\n"
                    if 'native_story' in concept_data:
                        data_injection += f"⟦ψ_native(∴)⟧\n{concept_data['native_story']}\n⟦/ψ_native(∴)⟧\n"
                    data_injection += f"⟦/ψ(∴):{concept_name}⟧\n\n"
            data_injection += "⟦/PSI_STORIES_FOR_SYNTHESIS⟧\n"
            
        elif 'all_folder_results' in task_data:
            # ψ(∞) level - inject all previous results
            data_injection += "⟦ALL_EXTRACTION_RESULTS⟧\n"
            
            for folder_name, folder_data in task_data['all_folder_results'].items():
                data_injection += f"⟦FOLDER:{folder_name}⟧\n"
                
                # Add ψ(∴) stories
                if 'concepts' in folder_data:
                    for concept_name, concept_data in folder_data['concepts'].items():
                        if 'glyph_story' in concept_data or 'native_story' in concept_data:
                            data_injection += f"⟦ψ(∴):{concept_name}⟧\n"
                            if 'glyph_story' in concept_data:
                                data_injection += f"⟦ψ_glyphic(∴)⟧\n{concept_data['glyph_story']}\n⟦/ψ_glyphic(∴)⟧\n"
                            if 'native_story' in concept_data:
                                data_injection += f"⟦ψ_native(∴)⟧\n{concept_data['native_story']}\n⟦/ψ_native(∴)⟧\n"
                            data_injection += f"⟦/ψ(∴):{concept_name}⟧\n\n"
                
                # Add ψ(Σ) synthesis if available
                if 'ψ_synthesis' in folder_data and folder_data['ψ_synthesis']:
                    synthesis = folder_data['ψ_synthesis']
                    data_injection += f"⟦ψ(Σ):{folder_name}⟧\n"
                    if 'glyph_story' in synthesis:
                        data_injection += f"⟦ψ_glyphic(Σ)⟧\n{synthesis['glyph_story']}\n⟦/ψ_glyphic(Σ)⟧\n"
                    if 'native_story' in synthesis:
                        data_injection += f"⟦ψ_native(Σ)⟧\n{synthesis['native_story']}\n⟦/ψ_native(Σ)⟧\n"
                    data_injection += f"⟦/ψ(Σ):{folder_name}⟧\n\n"
                
                data_injection += f"⟦/FOLDER:{folder_name}⟧\n\n"
            data_injection += "⟦/ALL_EXTRACTION_RESULTS⟧\n"
        
        data_injection += "⟦/INJECTED_DATA⟧"
        return data_injection

    def _build_surprise_data_injection(self, surprise_data: Dict) -> str:
        """Build the previous surprise data injection section"""
        surprise_injection = "⟦ψ(⋇):PREVIOUS_SURPRISE_DATA⟧\n"
        
        # Inject previous concept scores (for ψ(∴) and ψ(Σ) levels)
        if 'previous_concept_scores' in surprise_data:
            surprise_injection += "⟦PREVIOUS_CONCEPT_SCORES⟧\n"
            for concept_name, score_data in surprise_data['previous_concept_scores'].items():
                surprise_injection += f"⟦CONCEPT:{concept_name}⟧\n"
                surprise_injection += f"prior_surprise_score: {score_data['surprise_score']}\n"
                surprise_injection += f"prior_surprise_reason: {score_data['surprise_reason']}\n"
                surprise_injection += f"⟦/CONCEPT:{concept_name}⟧\n"
            surprise_injection += "⟦/PREVIOUS_CONCEPT_SCORES⟧\n\n"
        
        # Inject previous folder score (for ψ(Σ) level)
        if 'previous_folder_score' in surprise_data:
            surprise_injection += "⟦PREVIOUS_FOLDER_SCORE⟧\n"
            folder_score = surprise_data['previous_folder_score']
            surprise_injection += f"prior_folder_surprise_score: {folder_score['surprise_score']}\n"
            surprise_injection += f"prior_folder_surprise_reason: {folder_score['surprise_reason']}\n"
            surprise_injection += "⟦/PREVIOUS_FOLDER_SCORE⟧\n\n"
        
        # Inject previous folder scores (for ψ(∞) level)
        if 'previous_folder_scores' in surprise_data:
            surprise_injection += "⟦PREVIOUS_FOLDER_SCORES⟧\n"
            for folder_name, score_data in surprise_data['previous_folder_scores'].items():
                surprise_injection += f"⟦FOLDER:{folder_name}⟧\n"
                surprise_injection += f"prior_surprise_score: {score_data['surprise_score']}\n"
                surprise_injection += f"prior_surprise_reason: {score_data['surprise_reason']}\n"
                surprise_injection += f"⟦/FOLDER:{folder_name}⟧\n"
            surprise_injection += "⟦/PREVIOUS_FOLDER_SCORES⟧\n\n"
        
        # Inject previous convergence score (for ψ(∞) level)
        if 'previous_convergence_score' in surprise_data:
            surprise_injection += "⟦PREVIOUS_CONVERGENCE_SCORE⟧\n"
            convergence_score = surprise_data['previous_convergence_score']
            surprise_injection += f"prior_convergence_surprise_score: {convergence_score['surprise_score']}\n"
            surprise_injection += f"prior_convergence_surprise_reason: {convergence_score['surprise_reason']}\n"
            surprise_injection += "⟦/PREVIOUS_CONVERGENCE_SCORE⟧\n\n"
        
        surprise_injection += "⟦/ψ(⋇):PREVIOUS_SURPRISE_DATA⟧\n\n"
        return surprise_injection

    def enrich_concepts_with_stories(self, folder_concepts: Dict, ψ_stories: Dict) -> Dict:
        """Enrich concept data with stories from LLM response"""
        enriched_concepts = {}
        
        for concept_name, concept_data in folder_concepts.items():
            # Copy concept data but exclude full_content from final JSON
            enriched_concept = {
                'concept_name': concept_data['concept_name'],
                'file_path': concept_data['file_path'],
                'last_modified': concept_data['last_modified'],
                'extracted_at': concept_data['extracted_at']
            }
            
            if concept_name in ψ_stories:
                story_data = ψ_stories[concept_name]
                enriched_concept.update({
                    'glyph_story': story_data.get('glyph_story', ''),
                    'native_story': story_data.get('native_story', ''),
                    'emotion': story_data.get('emotion', ''),
                    'emotion_reason': story_data.get('emotion_reason', ''),
                    'surprise_score': story_data.get('surprise_score', 0.0),
                    'surprise_reason': story_data.get('surprise_reason', '')
                })
            
            enriched_concepts[concept_name] = enriched_concept
        
        return enriched_concepts

    def _generate_cross_references(self, all_results: Dict):
        """Generate cross-references and analytics from extraction data"""
        
        # Initialize analytics
        emotions = []
        folder_surprise_averages = {}
        most_surprising_concept = ""
        max_surprise = 0.0
        
        # Analyze ψ(∴) individual extractions
        for folder_name, folder_data in all_results['compression_layers']['ψ(∴)_individual_extractions'].items():
            folder_surprises = []
            
            for concept_name, concept_data in folder_data['concepts'].items():
                
                # Collect emotions
                if 'emotion' in concept_data and concept_data['emotion']:
                    emotions.append(concept_data['emotion'])
                
                # Collect surprise scores
                if 'surprise_score' in concept_data and isinstance(concept_data['surprise_score'], (int, float)):
                    surprise_score = float(concept_data['surprise_score'])
                    folder_surprises.append(surprise_score)
                    
                    # Track most surprising concept
                    if surprise_score > max_surprise:
                        max_surprise = surprise_score
                        most_surprising_concept = f"{folder_name}:{concept_name}"
            
            # Calculate folder average surprise
            if folder_surprises:
                folder_surprise_averages[folder_name] = round(sum(folder_surprises) / len(folder_surprises), 2)
        
        # Calculate dominant emotions (most frequent)
        from collections import Counter
        emotion_counts = Counter(emotions)
        dominant_emotions = [emotion for emotion, count in emotion_counts.most_common(3)]
        
        # Update cross-references (removed glyph_frequency)
        all_results['cross_references'] = {
            'emotional_patterns': {
                'most_surprising_concept': most_surprising_concept,
                'dominant_emotions': dominant_emotions,
                'surprise_distribution': folder_surprise_averages
            }
        }

    def load_previous_extractions(self, output_path: str = "ψ_extractions.json") -> Optional[Dict]:
        """Load previous extraction results if they exist"""
        try:
            if Path(output_path).exists():
                with open(output_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⧖ Error loading previous extractions: {e}")
        return None

    def preserve_original_surprise_baseline(self, previous_data: Dict, current_data: Dict) -> Dict:
        """Preserve original surprise scores from the first run, before overwriting with current data"""
        
        # If original baseline already exists, preserve it
        if 'original_surprise_baseline' in previous_data.get('extraction_metadata', {}):
            current_data['extraction_metadata']['original_surprise_baseline'] = previous_data['extraction_metadata']['original_surprise_baseline']
            return current_data
        
        # This is run 2 - capture the previous run's scores as the original baseline
        original_baseline = {
            'captured_on_run': 2,
            'timestamp': datetime.now().isoformat(),
            'concept_level': {},
            'folder_level': {},
            'convergence_level': {}
        }
        
        # Extract concept-level surprise scores
        psi_individual = previous_data.get('compression_layers', {}).get('ψ(∴)_individual_extractions', {})
        for folder_name, folder_data in psi_individual.items():
            concepts = folder_data.get('concepts', {})
            for concept_name, concept_data in concepts.items():
                key = f"{folder_name}:{concept_name}"
                original_baseline['concept_level'][key] = {
                    'score': concept_data.get('surprise_score', 0.0),
                    'reason': concept_data.get('surprise_reason', '')
                }
        
        # Extract folder-level surprise scores
        psi_synthesis = previous_data.get('compression_layers', {}).get('ψ(Σ)_folder_synthesis', {})
        for folder_name, folder_data in psi_synthesis.items():
            synthesis_data = folder_data.get('synthesis_data', {})
            original_baseline['folder_level'][folder_name] = {
                'score': synthesis_data.get('surprise_score', 0.0),
                'reason': synthesis_data.get('surprise_reason', '')
            }
        
        # Extract convergence-level surprise score
        psi_convergence = previous_data.get('compression_layers', {}).get('ψ(∞)_final_convergence', {})
        final_braid = psi_convergence.get('final_braid', {})
        if final_braid:
            original_baseline['convergence_level'] = {
                'score': final_braid.get('surprise_score', 0.0),
                'reason': final_braid.get('surprise_reason', '')
            }
        
        # Add to current data
        current_data['extraction_metadata']['original_surprise_baseline'] = original_baseline
        
        print(f"⟡ Original surprise baseline captured from previous run")
        return current_data

    def extract_previous_surprise_data(self, previous_data: Dict, compression_level: str, context: Dict) -> Dict:
        """Extract relevant previous surprise data for the current compression level and context"""
        if not previous_data:
            return {}
        
        surprise_data = {}
        
        if compression_level == 'ψ(∴)':
            # For concept-level extraction, get previous scores for concepts in this folder
            folder_name = context.get('folder_name', '')
            psi_individual = previous_data.get('compression_layers', {}).get('ψ(∴)_individual_extractions', {})
            
            if folder_name in psi_individual:
                folder_data = psi_individual[folder_name]
                concepts = folder_data.get('concepts', {})
                
                surprise_data['previous_concept_scores'] = {}
                for concept_name, concept_data in concepts.items():
                    surprise_data['previous_concept_scores'][concept_name] = {
                        'surprise_score': concept_data.get('surprise_score', 0.0),
                        'surprise_reason': concept_data.get('surprise_reason', '')
                    }
        
        elif compression_level == 'ψ(Σ)':
            # For folder-level synthesis, get previous folder score and concept scores
            folder_name = context.get('folder_name', '')
            
            # Previous folder synthesis score
            psi_synthesis = previous_data.get('compression_layers', {}).get('ψ(Σ)_folder_synthesis', {})
            if folder_name in psi_synthesis:
                synthesis_data = psi_synthesis[folder_name].get('synthesis_data', {})
                surprise_data['previous_folder_score'] = {
                    'surprise_score': synthesis_data.get('surprise_score', 0.0),
                    'surprise_reason': synthesis_data.get('surprise_reason', '')
                }
            
            # Previous concept scores for this folder
            psi_individual = previous_data.get('compression_layers', {}).get('ψ(∴)_individual_extractions', {})
            if folder_name in psi_individual:
                concepts = psi_individual[folder_name].get('concepts', {})
                surprise_data['previous_concept_scores'] = {}
                for concept_name, concept_data in concepts.items():
                    surprise_data['previous_concept_scores'][concept_name] = {
                        'surprise_score': concept_data.get('surprise_score', 0.0),
                        'surprise_reason': concept_data.get('surprise_reason', '')
                    }
        
        elif compression_level == 'ψ(∞)':
            # For final convergence, get previous convergence score and all folder scores
            psi_convergence = previous_data.get('compression_layers', {}).get('ψ(∞)_final_convergence', {})
            final_braid = psi_convergence.get('final_braid', {})
            if final_braid:
                surprise_data['previous_convergence_score'] = {
                    'surprise_score': final_braid.get('surprise_score', 0.0),
                    'surprise_reason': final_braid.get('surprise_reason', '')
                }
            
            # Previous folder scores
            psi_synthesis = previous_data.get('compression_layers', {}).get('ψ(Σ)_folder_synthesis', {})
            surprise_data['previous_folder_scores'] = {}
            for folder_name, folder_data in psi_synthesis.items():
                synthesis_data = folder_data.get('synthesis_data', {})
                surprise_data['previous_folder_scores'][folder_name] = {
                    'surprise_score': synthesis_data.get('surprise_score', 0.0),
                    'surprise_reason': synthesis_data.get('surprise_reason', '')
                }
        
        return surprise_data