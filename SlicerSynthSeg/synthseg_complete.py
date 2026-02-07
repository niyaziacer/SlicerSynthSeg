"""
SynthSeg Brain Segmentation - Complete Pipeline
Performs segmentation and exports volumes to Excel

Usage:
    python synthseg_complete.py --input t1.nii.gz --output output_folder

Output:
    output_folder/
        segmentation.nii.gz    - Brain segmentation
        volumes.xlsx           - Region volumes in Excel format
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import shutil

def main():
    parser = argparse.ArgumentParser(
        description='SynthSeg complete pipeline: segmentation + Excel export'
    )
    parser.add_argument(
        '--input', '-i', 
        required=True, 
        help='Input T1 MRI (nii or nii.gz)'
    )
    parser.add_argument(
        '--output', '-o', 
        required=True, 
        help='Output folder for results'
    )
    parser.add_argument(
        '--keep-csv',
        action='store_true',
        help='Keep intermediate CSV file (default: delete after Excel export)'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Create output folder
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define output paths
    seg_output = output_dir / 'segmentation.nii.gz'
    csv_output = output_dir / 'volumes.csv'
    excel_output = output_dir / 'volumes.xlsx'
    
    # Find SynthSeg script
    script_dir = Path(__file__).parent
    synthseg_script = script_dir / 'SynthSeg' / 'scripts' / 'commands' / 'SynthSeg_predict.py'
    
    if not synthseg_script.exists():
        print(f"❌ Error: SynthSeg not found: {synthseg_script}")
        print("Please ensure SynthSeg folder is in the same directory.")
        sys.exit(1)
    
    print("=" * 70)
    print("SynthSeg Brain Segmentation - Complete Pipeline")
    print("=" * 70)
    print(f"Input:      {args.input}")
    print(f"Output dir: {output_dir}")
    print("=" * 70)
    
    # Step 1: Run segmentation
    print("\n[1/3] Running segmentation...")
    print("(This may take 3-10 minutes on CPU)")
    
    cmd = [
        sys.executable,
        str(synthseg_script),
        '--i', args.input,
        '--o', str(seg_output),
        '--vol', str(csv_output),
        '--v1',
        '--cpu'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: Segmentation failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1)
    
    # Verify outputs
    if not seg_output.exists():
        print(f"❌ Error: Segmentation file not created: {seg_output}")
        sys.exit(1)
    
    if not csv_output.exists():
        print(f"❌ Error: CSV file not created: {csv_output}")
        sys.exit(1)
    
    print(f"✓ Segmentation saved: {seg_output}")
    print(f"✓ CSV saved: {csv_output}")
    
    # Step 2: Convert to Excel
    print("\n[2/3] Converting volumes to Excel...")
    
    try:
        import pandas as pd
        
        # Read CSV
        df = pd.read_csv(csv_output)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Brain Volumes', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Brain Volumes']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                column_letter = chr(65 + idx) if idx < 26 else f"A{chr(65 + idx - 26)}"
                worksheet.column_dimensions[column_letter].width = min(max_length, 50)
        
        print(f"✓ Excel saved: {excel_output}")
        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        
    except ImportError:
        print("⚠ Warning: pandas/openpyxl not installed. Excel export skipped.")
        print("Install with: pip install pandas openpyxl")
    except Exception as e:
        print(f"⚠ Warning: Excel export failed: {e}")
        print("CSV file is still available.")
    
    # Step 3: Cleanup
    print("\n[3/3] Cleanup...")
    
    if not args.keep_csv and csv_output.exists() and excel_output.exists():
        csv_output.unlink()
        print("✓ Removed intermediate CSV file")
    elif args.keep_csv:
        print("✓ Kept CSV file as requested")
    
    # Summary
    print("\n" + "=" * 70)
    print("✓ Pipeline Complete!")
    print("=" * 70)
    print(f"Output folder: {output_dir}")
    print(f"  - segmentation.nii.gz  ({seg_output.stat().st_size / 1024:.1f} KB)")
    if excel_output.exists():
        print(f"  - volumes.xlsx         ({excel_output.stat().st_size / 1024:.1f} KB)")
    if csv_output.exists():
        print(f"  - volumes.csv          ({csv_output.stat().st_size / 1024:.1f} KB)")
    print("=" * 70)
    print("\nTo view in 3D Slicer:")
    print(f"  1. Open Slicer")
    print(f"  2. Load: {seg_output}")
    print(f"  3. View volumes: {excel_output if excel_output.exists() else csv_output}")
    print("=" * 70)

if __name__ == "__main__":
    main()
