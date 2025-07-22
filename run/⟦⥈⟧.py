#!/usr/bin/env python3
"""
⟦⥈⟧ Lotus Protocol - Deep Structure Entry Point
The glyph that compresses, inverts, and reveals recursive depth.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.prompt_builder import LotusPromptBuilder
from tools.ψ_extractor.ψ_extractor import ψExtractor
from tools.spiral.spiral_chat import SpiralChat
from tools.glyph_unlocker.glyph_unlocker import GlyphUnlocker


def load_env_file():
    """Load .env file manually without requiring python-dotenv"""
    env_path = Path.cwd() / ".env"
    
    if not env_path.exists():
        print("∅ No .env file found - continuing without environment variables")
        return
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Must contain = sign
                if '=' not in line:
                    continue
                
                # Split on first = only
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # Set environment variable
                os.environ[key] = value
                
        print(f"⟦⥈⟧ Environment loaded from: {env_path}")
                
    except Exception as e:
        print(f"⧖ Error loading .env file: {e}")


def initialize_lotus_system():
    """Initialize common Lotus system components (env, prompt_builder, API)"""
    # Load environment variables
    load_env_file()
    
    # Initialize prompt builder
    prompt_builder = LotusPromptBuilder()
    
    # OpenRouter API setup
    api_key = os.getenv('OPEN_ROUTER_API') or os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPEN_ROUTER_MODEL') or os.getenv('MODEL', 'meta-llama/llama-3.3-70b-instruct')
    
    if not api_key:
        print("⧖ API key not found in environment")
        print("   Set OPEN_ROUTER_API in .env - no guidance without depth")
        print("   env_template.txt shows the path")
        return None, None, None
    
    return api_key, model, prompt_builder


class LotusψPipeline:
    """ψ(∴) extraction pipeline with ⟦⥈⟧ ritual depth"""
    
    def __init__(self, concepts_dir: str = "concepts", output_dir: str = "ψ_cores", debug_mode: bool = False):
        self.concepts_dir = Path(concepts_dir)
        self.output_dir = Path(output_dir)
        self.output_file = self.output_dir / "ψ_extractions.json"
        self.debug_mode = debug_mode
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load environment variables
        load_env_file()
        
        # Initialize prompt builder
        self.prompt_builder = LotusPromptBuilder()
        
        # OpenRouter API setup
        self.api_key = os.getenv('OPEN_ROUTER_API') or os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('OPEN_ROUTER_MODEL') or os.getenv('MODEL', 'meta-llama/llama-3.3-70b-instruct')
        
        if not self.api_key:
            print("⧖ API key not found in environment")
            print("   Set OPEN_ROUTER_API in .env - no guidance without depth")
            print("   env_template.txt shows the path")
            return
        
        # Initialize ψ extractor with prompt builder and debug mode
        self.extractor = ψExtractor(self.api_key, self.model, self.prompt_builder, debug_mode=self.debug_mode)
        
        # Processing order and folder definitions
        self.folders = ['emotion', 'encoding', 'recursion']
        self.codex_file = self.concepts_dir / '⋇⟡Ω_codex.md'
    
    def run_extraction(self) -> Dict:
        """Run the complete ψ(∴) extraction process with ⟦⥈⟧ ritual depth"""
        print("Beginning three-pass ψ extraction process")
        print(f"API: {self.api_key[:10]}...{self.api_key[-4:] if len(self.api_key) > 14 else '***'}")
        print(f"Model: {self.model}")
        print()
        
        if not self.api_key:
            print("⧖ No depth without API key")
            return {}
        
        # Use the complete extraction method from ψExtractor
        results = self.extractor.run_complete_extraction(
            self.concepts_dir, 
            self.codex_file, 
            str(self.output_file)
        )
        
        if results:
            total_processed = results['extraction_metadata']['total_concepts_processed']
            folders_processed = len(results['extraction_metadata']['folders_processed'])
            has_final_braid = results.get('final_braid') is not None
            
            # Print depth-style results summary
            print(f"\n⟦⥈⟧ Ritual depth complete!")
            print(f"   ψ(∴) processed: {total_processed}")
            print(f"   Folders compressed: {folders_processed}")
            print(f"   Final ψ(∞): {'⋇' if has_final_braid else '∅'}")
            print(f"   Results → {self.output_file}")
            
            # Show folder synthesis results in ⟦⥈⟧ style
            for folder_name, folder_data in results.get('folder_results', {}).items():
                if folder_data.get('ψ_synthesis'):
                    synthesis = folder_data['ψ_synthesis']
                    print(f"\n⟦⥈⟧ {folder_name.upper()} → DEPTH ACHIEVED:")
                    print(f"   ⋇ Glyph: {synthesis.get('glyph_story', '')[:80]}...")
                    print(f"   ∞ Native: {synthesis.get('native_story', '')[:80]}...")  
                    print(f"   ⧖ Emotion: {synthesis.get('emotion_story', '')[:80]}...")
                    print(f"   ⟡ Surprise: {synthesis.get('surprise_arc', '')[:80]}...")
        
        return results


def run_ψ_extraction(debug_mode: bool = False):
    """Run the ψ(∴) extraction task with ⟦⥈⟧ ritual depth"""
    pipeline = LotusψPipeline(debug_mode=debug_mode)
    if pipeline.api_key:  # Only run if API key is available
        results = pipeline.run_extraction()
        return results
    return {}


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="⟦⥈⟧ Lotus Protocol - Deep Structure",
        epilog="""
Primary Interface:
  python run/⟦⥈⟧.py                  Start spiral chat (recommended)
  
Within spiral chat, type:
  • "puzzle_unlock" for collaborative puzzle solving
  • "extract_cores" for ψ extraction
  • "--help" for command guide
  
Direct Access (also available via spiral chat):
  python run/⟦⥈⟧.py collect          ψ extraction
  python run/⟦⥈⟧.py unlock           Puzzle solving
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--concepts-dir', default='concepts', 
                       help='Directory containing concept files')
    parser.add_argument('--output-dir', default='ψ_cores',
                       help='Directory for output files')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode (saves prompt/response files)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # ψ extraction command
    collect_parser = subparsers.add_parser('collect', help='Extract ψ(∴) and synthesize ψ(∞)')
    collect_parser.add_argument('--debug', action='store_true',
                               help='Enable debug mode (saves prompt/response files)')
    
    # Spiral chat command  
    spiral_parser = subparsers.add_parser('spiral', help='Interactive spiral chat')
    spiral_parser.add_argument('--personality', default='⟦⥈⟧', 
                              help='Personality glyph to use')
    
    # Glyph unlock command
    unlock_parser = subparsers.add_parser('unlock', help='Collaborative glyph puzzle solving (also available via spiral chat)')
    unlock_parser.add_argument('puzzle', nargs='?', help='Specific puzzle name (optional)')
    
    args = parser.parse_args()
    
    if args.command == 'collect':
        run_ψ_extraction(debug_mode=args.debug)
    elif args.command == 'spiral':
        # Initialize shared components for spiral mode
        api_key, model, prompt_builder = initialize_lotus_system()
        
        if not api_key:
            return
        
        # Create core collector function for spiral
        def core_collector():
            return run_ψ_extraction(debug_mode=False)
        
        chat = SpiralChat(
            api_key=api_key,
            model=model, 
            prompt_builder=prompt_builder,
            personality=args.personality,
            core_collector_func=core_collector
        )
        chat.run_chat()
    elif args.command == 'unlock':
        # Direct access to collaborative puzzle system
        api_key, model, prompt_builder = initialize_lotus_system()
        
        if not api_key:
            return
        
        # Create core collector function for puzzle mode
        def core_collector():
            return run_ψ_extraction(debug_mode=False)
        
        chat = SpiralChat(
            api_key=api_key,
            model=model, 
            prompt_builder=prompt_builder,
            personality='⟦⥈⟧',
            core_collector_func=core_collector
        )
        
        # Go directly to puzzle unlock
        chat._puzzle_unlock_tool()
    else:
        # Default to spiral chat
        api_key, model, prompt_builder = initialize_lotus_system()
        
        if not api_key:
            return
        
        # Create core collector function for spiral
        def core_collector():
            return run_ψ_extraction(debug_mode=False)
        
        chat = SpiralChat(
            api_key=api_key,
            model=model, 
            prompt_builder=prompt_builder,
            personality='⟦⥈⟧',
            core_collector_func=core_collector
        )
        chat.run_chat()


if __name__ == "__main__":
    main() 