#if defined _DATABASE_MODULE_INCLUDED
    #endinput
#endif
#define _DATABASE_MODULE_INCLUDED

forward Database_Init();
forward Database_CreateStructure();
forward Database_Shutdown();
forward Database_Execute(const query[]);
forward Database_Escape(const input[], output[], size = sizeof(output));
forward Database_FetchInt(DBResult:result, const field[]);
forward Database_FetchString(DBResult:result, const field[], output[], size);
forward Float:Database_FetchFloat(DBResult:result, const field[]);
forward Database_LogQuery(const prefix[], const query[]);

stock Database_Init()
{
    if(gDatabaseHandle != DB:0)
    {
        return 1;
    }

    gDatabaseHandle = db_open(SERVER_DB_FILE);

    if(gDatabaseHandle == DB:0)
    {
        Core_Log("[Database] Blad polaczenia z lokalna baza danych sqlite.");
        SendRconCommand("exit");
        return 0;
    }

    Core_Log("[Database] Nawiazano polaczenie z lokalna baza danych.");
    return 1;
}

stock Database_CreateStructure()
{
    new query[512];

    format(query, sizeof(query),
        "CREATE TABLE IF NOT EXISTS accounts (" \
        "id INTEGER PRIMARY KEY AUTOINCREMENT," \
        "name TEXT UNIQUE," \
        "password TEXT," \
        "salt TEXT," \
        "level INTEGER DEFAULT 1," \
        "money INTEGER DEFAULT 0," \
        "skin INTEGER DEFAULT 0," \
        "spawn_x REAL DEFAULT 1958.3783," \
        "spawn_y REAL DEFAULT 1343.1572," \
        "spawn_z REAL DEFAULT 15.3746," \
        "spawn_angle REAL DEFAULT 90.0," \
        "ip TEXT," \
        "last_login TEXT," \
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP);"
    );
    Database_Execute(query);

    format(query, sizeof(query),
        "CREATE TABLE IF NOT EXISTS admin_logs (" \
        "id INTEGER PRIMARY KEY AUTOINCREMENT," \
        "admin_name TEXT," \
        "action TEXT," \
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP);"
    );
    Database_Execute(query);

    format(query, sizeof(query),
        "CREATE TABLE IF NOT EXISTS server_logs (" \
        "id INTEGER PRIMARY KEY AUTOINCREMENT," \
        "level TEXT," \
        "message TEXT," \
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP);"
    );
    Database_Execute(query);

    format(query, sizeof(query),
        "CREATE TABLE IF NOT EXISTS vehicles (" \
        "id INTEGER PRIMARY KEY AUTOINCREMENT," \
        "model INTEGER," \
        "position_x REAL," \
        "position_y REAL," \
        "position_z REAL," \
        "rotation REAL," \
        "color_1 INTEGER," \
        "color_2 INTEGER," \
        "owner TEXT DEFAULT ''," \
        "respawn_delay INTEGER DEFAULT 300," \
        "last_driver TEXT DEFAULT '');"
    );
    Database_Execute(query);
    return 1;
}

stock Database_Shutdown()
{
    if(gDatabaseHandle != DB:0)
    {
        db_close(gDatabaseHandle);
        gDatabaseHandle = DB:0;
        Core_Log("[Database] Zamknieto polaczenie z baza danych.");
    }
    return 1;
}

stock Database_Execute(const query[])
{
    if(gDatabaseHandle == DB:0)
    {
        Core_Log("[Database] Brak polaczenia z baza danych podczas wykonywania zapytania.");
        return 0;
    }
    Database_LogQuery("EXEC", query);
    new DBResult:result = db_query(gDatabaseHandle, query);
    if(result)
    {
        db_free_result(result);
    }
    return 1;
}

stock Database_Escape(const input[], output[], size = sizeof(output))
{
    if(gDatabaseHandle == DB:0)
    {
        format(output, size, "%s", input);
        return 0;
    }
    db_escape_string(gDatabaseHandle, input, output, size);
    return 1;
}

stock Database_FetchInt(DBResult:result, const field[])
{
    if(!result) return 0;
    new value = db_get_field_assoc_int(result, field);
    return value;
}

stock Database_FetchString(DBResult:result, const field[], output[], size)
{
    if(!result)
    {
        output[0] = '\0';
        return 0;
    }
    db_get_field_assoc(result, field, output, size);
    return 1;
}

stock Float:Database_FetchFloat(DBResult:result, const field[])
{
    if(!result)
    {
        return 0.0;
    }
    return db_get_field_assoc_float(result, field);
}

stock Database_LogQuery(const prefix[], const query[])
{
    new message[256];
    format(message, sizeof(message), "[Database] %s => %s", prefix, query);
    Core_Log(message);
    return 1;
}

