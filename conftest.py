# Prevent pytest from collecting source files whose names match *_test.py.
# The forecast_tool/diagnostics/stationarity_test.py module contains a function
# named test_stationarity(), which pytest mistakenly tries to collect as a test.
collect_ignore_glob = [
    "forecast_tool/diagnostics/*_test.py",
    "forecast_tool/validation/*_test.py",
]
