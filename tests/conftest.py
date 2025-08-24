"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure for testing."""
    project_dir = temp_dir / "sample_project"
    project_dir.mkdir()
    
    # Create package.json
    (project_dir / "package.json").write_text('''{
  "name": "sample-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "test": "jest",
    "lint": "eslint src/"
  },
  "devDependencies": {
    "typescript": "^4.0.0",
    "jest": "^27.0.0",
    "eslint": "^8.0.0"
  }
}''')
    
    # Create tsconfig.json
    (project_dir / "tsconfig.json").write_text('''{
  "compilerOptions": {
    "target": "es2020",
    "module": "commonjs",
    "outDir": "./dist",
    "rootDir": "./src"
  }
}''')
    
    # Create source files
    src_dir = project_dir / "src"
    src_dir.mkdir()
    
    (src_dir / "index.ts").write_text('''
export function greet(name: string): string {
    return `Hello, ${name}!`;
}

export class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
    
    multiply(a: number, b: number): number {
        return a * b;
    }
}
''')
    
    (src_dir / "utils.ts").write_text('''
import fs from 'fs';

export function readFile(path: string): string {
    return fs.readFileSync(path, 'utf-8');
}

export const Constants = {
    API_URL: 'https://api.example.com',
    TIMEOUT: 5000
} as const;
''')
    
    # Create test files
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    
    (tests_dir / "index.test.ts").write_text('''
import { greet, Calculator } from '../src/index';

describe('greet function', () => {
    it('should greet with name', () => {
        expect(greet('World')).toBe('Hello, World!');
    });
});

describe('Calculator', () => {
    const calc = new Calculator();
    
    it('should add numbers', () => {
        expect(calc.add(2, 3)).toBe(5);
    });
    
    it('should multiply numbers', () => {
        expect(calc.multiply(4, 5)).toBe(20);
    });
});
''')
    
    return project_dir


@pytest.fixture
def python_project(temp_dir):
    """Create a Python project structure for testing."""
    project_dir = temp_dir / "python_project"
    project_dir.mkdir()
    
    # Create pyproject.toml
    (project_dir / "pyproject.toml").write_text('''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "sample-python-project"
version = "1.0.0"
dependencies = [
    "requests>=2.25.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
''')
    
    # Create source files
    src_dir = project_dir / "src" / "mypackage"
    src_dir.mkdir(parents=True)
    
    (src_dir / "__init__.py").write_text('')
    
    (src_dir / "calculator.py").write_text('''
"""Simple calculator module."""

from typing import Union

Number = Union[int, float]


class Calculator:
    """A simple calculator class."""
    
    def add(self, a: Number, b: Number) -> Number:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: Number, b: Number) -> Number:
        """Subtract b from a.""" 
        return a - b
    
    def multiply(self, a: Number, b: Number) -> Number:
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a: Number, b: Number) -> Number:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
''')
    
    (src_dir / "utils.py").write_text('''
"""Utility functions."""

import json
from pathlib import Path
from typing import Any, Dict


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON from file."""
    return json.loads(file_path.read_text())


def save_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Save data to JSON file."""
    file_path.write_text(json.dumps(data, indent=2))


def format_number(num: float, decimals: int = 2) -> str:
    """Format number with specified decimal places."""
    return f"{num:.{decimals}f}"
''')
    
    # Create test files
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    
    (tests_dir / "__init__.py").write_text('')
    
    (tests_dir / "test_calculator.py").write_text('''
"""Tests for calculator module."""

import pytest
from src.mypackage.calculator import Calculator


class TestCalculator:
    """Test calculator functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.calc = Calculator()
    
    def test_add(self):
        """Test addition."""
        assert self.calc.add(2, 3) == 5
        assert self.calc.add(-1, 1) == 0
        assert self.calc.add(0.1, 0.2) == pytest.approx(0.3)
    
    def test_subtract(self):
        """Test subtraction."""
        assert self.calc.subtract(5, 3) == 2
        assert self.calc.subtract(0, 1) == -1
    
    def test_multiply(self):
        """Test multiplication."""
        assert self.calc.multiply(3, 4) == 12
        assert self.calc.multiply(-2, 3) == -6
    
    def test_divide(self):
        """Test division."""
        assert self.calc.divide(6, 2) == 3
        assert self.calc.divide(1, 3) == pytest.approx(0.333, rel=1e-2)
    
    def test_divide_by_zero(self):
        """Test division by zero raises error."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            self.calc.divide(1, 0)
''')
    
    return project_dir


@pytest.fixture
def mock_openrouter_response():
    """Mock OpenRouter API response."""
    return {
        "choices": [{
            "message": {
                "content": '''**ANALYSIS**
The current code has a basic structure but needs error handling improvements.

**PLAN**
1. Add try-catch blocks around API calls
2. Add input validation
3. Add logging statements

**PATCH**
```diff
--- src/api.ts
+++ src/api.ts
@@ -1,3 +1,8 @@
+import { logger } from './logger';
+
 export async function fetchData(url: string) {
-  const response = await fetch(url);
-  return response.json();
+  try {
+    logger.info('Fetching data from:', url);
+    const response = await fetch(url);
+    if (!response.ok) {
+      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
+    }
+    return await response.json();
+  } catch (error) {
+    logger.error('Failed to fetch data:', error);
+    throw error;
+  }
 }
```

**COMMIT MESSAGE**
Add error handling and logging to API calls

**TEST PLAN**
1. Test successful API calls
2. Test error scenarios (404, 500, network errors)
3. Verify logging output

**ROLLBACK**
Use `git restore src/api.ts` to revert changes
'''
            }
        }]
    }


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = Mock()
    config.openrouter_api_key = "test-key"
    config.openrouter_model = "test/model"
    config.openrouter_headers = {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json"
    }
    return config


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before/after tests."""
    # Store original values
    original_env = dict(os.environ)
    
    # Clear DevAgent-related env vars
    for key in list(os.environ.keys()):
        if key.startswith(('OPENROUTER_', 'LOG_', 'MAX_', 'RATE_')):
            del os.environ[key]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)