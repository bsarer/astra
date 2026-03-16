import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch
from agent import run_python_code


class TestRunPythonCodeStdoutCapture:
    def test_captures_print_output(self):
        result = run_python_code.invoke({"code": "print('hello world')"})
        assert "hello world" in result

    def test_captures_result_variable(self):
        result = run_python_code.invoke({"code": "result = 42"})
        assert "42" in result

    def test_empty_code_returns_empty(self):
        result = run_python_code.invoke({"code": ""})
        assert result == ""


class TestRunPythonCodeExceptionHandling:
    def test_returns_error_on_exception(self):
        result = run_python_code.invoke({"code": "raise ValueError('test error')"})
        assert "Error executing code" in result
        assert "test error" in result

    def test_returns_error_on_syntax_error(self):
        result = run_python_code.invoke({"code": "def ("})
        assert "Error" in result

    def test_returns_error_on_name_error(self):
        result = run_python_code.invoke({"code": "print(undefined_var)"})
        assert "Error executing code" in result


class TestRunPythonCodeTimeout:
    def test_timeout_returns_error_message(self):
        # Patch TIMEOUT_SECONDS inside the function isn't easy, so we mock
        # the ThreadPoolExecutor to simulate a timeout
        from concurrent.futures import TimeoutError

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_pool_cls:
            mock_executor = mock_pool_cls.return_value.__enter__.return_value
            mock_future = mock_executor.submit.return_value
            mock_future.result.side_effect = TimeoutError()

            result = run_python_code.invoke({"code": "import time; time.sleep(100)"})
            assert "timed out" in result
            assert "30 seconds" in result

    def test_normal_code_does_not_timeout(self):
        result = run_python_code.invoke({"code": "print('fast')"})
        assert "timed out" not in result
        assert "fast" in result
