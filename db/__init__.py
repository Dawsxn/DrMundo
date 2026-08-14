"""Data-access layer: the ONLY place SQL lives.

All functions here use raw, parameterized sqlite3 (no ORM, no text-to-SQL). The LLM
selects which function to call and with what arguments; it never writes SQL itself.
"""
