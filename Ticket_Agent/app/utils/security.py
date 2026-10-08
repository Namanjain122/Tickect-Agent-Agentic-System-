def is_safe_sql(sql: str) -> bool:
    """Check if SQL query is safe to execute"""
    dangerous_commands = ["DROP", "DELETE", "UPDATE", "ALTER", "TRUNCATE", "INSERT", "EXEC", "EXECUTE", "MERGE"]
    sql_upper = sql.upper().strip()
    
    # First word check
    first_word = sql_upper.split()[0] if sql_upper.split() else ""
    if first_word in dangerous_commands:
        return False
    # Semicolon check for multiple commands
    if ";" in sql_upper:
        for part in sql_upper.split(";")[1:]:
            part_words = part.strip().split()
            if part_words and part_words[0] in dangerous_commands:
                return False
    return True