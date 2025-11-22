import pytest
from unittest.mock import Mock, patch
from singularity.code import safety


class FakeFunction:
    def __init__(self, return_value=None, raise_exception=None):
        self.return_value = return_value
        self.raise_exception = raise_exception
        self.__name__ = "FakeFunction" 
    
    def __call__(self, *args, **kwargs):
        if self.raise_exception:
            raise self.raise_exception
        return self.return_value


def test_buffer_writes():
    buffer = safety.Buffer("start: ")
    buffer.write("first ")
    buffer.write("second")
    assert buffer.data == "start: first second"



#GET_TIMESTAMP

def test_get_timestamp_with_specific_time():
    import time
    result = safety.get_timestamp(0) 
    assert isinstance(result, str)
    assert time.tzname[time.daylight] in result


# LOG_ERROR
def test_log_error_writes_to_stderr(capsys):
    safety.log_error("test error: %d", 404)
    captured = capsys.readouterr() #zachytu vsetko c obolo vonku na stderr
    assert "test error: 404" in captured.err


@patch('logging.getLogger')
def test_log_error_with_logger_handlers(mock_get_logger, capsys):
    mock_logger = Mock()
    mock_logger.handlers = [Mock()]  
    mock_get_logger.return_value = mock_logger
    
    safety.log_error("message: %s", "test")
    
    mock_logger.error.assert_called_once_with("message: %s", "test")
    captured = capsys.readouterr()
    assert "message: test" in captured.err


@patch('logging.getLogger')
def test_log_error_handles_ioerror(mock_get_logger, capsys):
    mock_logger = Mock()
    mock_logger.handlers = [Mock()]
    mock_logger.error.side_effect = IOError("denied")  # stub- namiesto bezneho spravania vyhodi vynimku
    mock_get_logger.return_value = mock_logger
    
    safety.log_error("Test")
    captured = capsys.readouterr()
    assert "Test" in captured.err



# LOG_FUNC_EXC
def test_log_func_exc_logs_exception_info(capsys):
    def failing_func():
        raise ValueError("test error")
    
    try:
        failing_func()
    except:
        safety.log_func_exc(failing_func)
    
    captured = capsys.readouterr()
    assert "failing_func" in captured.err
    assert "ValueError" in captured.err
    assert "test error" in captured.err
    assert "```" in captured.err


# SAFE_CALL
def test_safe_call_returns_result_on_success():
    fake = FakeFunction(return_value=67)
    result = safety.safe_call(fake)
    assert result == 67


def test_safe_call_returns_on_error_on_exception(capsys):
    safety.FIRST_ERROR = False 
    fake = FakeFunction(raise_exception=ValueError("Error"))
    
    result = safety.safe_call(fake, on_error="FAILED")
    
    assert result == "FAILED"
    captured = capsys.readouterr()
    assert "ValueError" in captured.err


# SAFE DEKORÁTOR
def test_safe_decorator_works_on_success():
    @safety.safe(on_error=-1)
    def multiply(x, y):
        return x * y
    
    assert multiply(3, 4) == 12


def test_safe_decorator_returns_on_error_on_exception(capsys):
    @safety.safe(on_error="FAIL")
    def divide(x, y):
        return x / y
    result = divide(10, 0)
    assert result == "FAIL"
    
    captured = capsys.readouterr()
    assert "ZeroDivisionError" in captured.err


