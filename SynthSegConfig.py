"""
SynthSeg Environment Configuration
Handles Python environment setup and validation
"""

import os
import json
import subprocess
import sys
from pathlib import Path


class SynthSegConfig:
    """Manage SynthSeg environment configuration"""
    
    def __init__(self, slicer_home=None):
        if slicer_home is None:
            # Try to detect Slicer home directory
            if sys.platform == "win32":
                slicer_home = os.path.expanduser("~/AppData/Roaming/NA-MIC")
            elif sys.platform == "darwin":
                slicer_home = os.path.expanduser("~/Library/Application Support/NA-MIC")
            else:
                slicer_home = os.path.expanduser("~/.config/NA-MIC")
        
        self.slicer_home = Path(slicer_home)
        self.config_file = self.slicer_home / "SlicerSynthSeg" / "config.json"
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_config(self, synthseg_path, python_path):
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config = {
            'synthseg_path': str(synthseg_path),
            'python_path': str(python_path)
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.config = config
        return True
    
    def validate_synthseg_path(self, path):
        """Validate SynthSeg installation"""
        path = Path(path)
        
        # Check if directory exists
        if not path.exists():
            return False, "Directory does not exist"
        
        # Check for predict script
        predict_script = path / "SynthSeg" / "predict_synthseg.py"
        if not predict_script.exists():
            return False, "SynthSeg/predict_synthseg.py not found"
        
        # Check for model
        model_dir = path / "models"
        if not model_dir.exists():
            return False, "models directory not found"
        
        model_v1 = model_dir / "synthseg_1.0.h5"
        if not model_v1.exists():
            return False, "synthseg_1.0.h5 model not found in models/"
        
        return True, "SynthSeg installation valid"
    
    def validate_python_env(self, python_path):
        """Validate Python environment has required packages"""
        python_path = Path(python_path)
        
        # Check if Python executable exists
        if not python_path.exists():
            return False, "Python executable not found"
        
        # Check for required packages
        required_packages = ['tensorflow', 'keras', 'nibabel', 'scipy', 'numpy']
        
        try:
            cmd = [str(python_path), '-c', 
                   'import tensorflow, keras, nibabel, scipy, numpy; print("OK")']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                missing = []
                for pkg in required_packages:
                    test_cmd = [str(python_path), '-c', f'import {pkg}']
                    test_result = subprocess.run(test_cmd, capture_output=True, timeout=5)
                    if test_result.returncode != 0:
                        missing.append(pkg)
                
                return False, f"Missing packages: {', '.join(missing)}"
            
            return True, "Python environment valid"
            
        except subprocess.TimeoutExpired:
            return False, "Python validation timed out"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_config(self):
        """Get current configuration"""
        return self.config
    
    def is_configured(self):
        """Check if environment is configured"""
        return ('synthseg_path' in self.config and 
                'python_path' in self.config and
                os.path.exists(self.config['synthseg_path']) and
                os.path.exists(self.config['python_path']))


def test_configuration():
    """Test current configuration"""
    config = SynthSegConfig()
    
    if not config.is_configured():
        print("No configuration found")
        return False
    
    current_config = config.get_config()
    print(f"SynthSeg path: {current_config['synthseg_path']}")
    print(f"Python path: {current_config['python_path']}")
    
    # Validate SynthSeg
    valid, msg = config.validate_synthseg_path(current_config['synthseg_path'])
    print(f"SynthSeg validation: {msg}")
    
    if not valid:
        return False
    
    # Validate Python
    valid, msg = config.validate_python_env(current_config['python_path'])
    print(f"Python validation: {msg}")
    
    return valid


if __name__ == "__main__":
    test_configuration()
