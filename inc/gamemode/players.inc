#if defined _PLAYERS_MODULE_INCLUDED
    #endinput
#endif
#define _PLAYERS_MODULE_INCLUDED

#define DIALOG_LOGIN 1000
#define DIALOG_REGISTER 1001
#define DIALOG_CHANGEPASS 1002

forward Players_Init();
forward Players_Shutdown();
forward Players_OnPlayerConnect(playerid);
forward Players_OnPlayerDisconnect(playerid, reason);
forward Players_OnPlayerRequestClass(playerid, classid);
forward Players_OnPlayerSpawn(playerid);
forward Players_OnPlayerCommandText(playerid, cmdtext[]);
forward Players_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[]);
forward Players_OnPlayerStateChange(playerid, newstate, oldstate);
forward Players_SaveAccount(playerid);
forward Players_LoadAccount(playerid);
forward Players_LoginPlayer(playerid, const password[]);
forward Players_RegisterPlayer(playerid, const password[]);
forward Players_ShowLoginDialog(playerid);
forward Players_ShowRegisterDialog(playerid);
forward Players_SpawnPlayer(playerid);
forward Players_UpdateSession(playerid);
forward Players_GenerateSalt(output[], length);
forward Players_LogEvent(playerid, const level[], const message[]);

stock Players_Init()
{
    UsePlayerPedAnims();
    EnableInteriorEnterExits();
    SetWorldTime(12);
    SetNameTagDrawDistance(50.0);
    AllowInteriorWeapons(0);
    return 1;
}

stock Players_Shutdown()
{
    for(new playerid = 0; playerid < MAX_PLAYERS; playerid++)
    {
        if(IsPlayerConnected(playerid) && PlayerData[playerid][pLogged])
        {
            Players_SaveAccount(playerid);
        }
    }
    return 1;
}

stock Players_OnPlayerConnect(playerid)
{
    Core_ResetPlayerData(playerid);
    PlayerData[playerid][pConnected] = true;

    new name[MAX_PLAYER_NAME + 1];
    GetPlayerName(playerid, name, sizeof(name));

    new ip[16];
    GetPlayerIp(playerid, ip, sizeof(ip));
    format(PlayerData[playerid][pIP], sizeof(PlayerData[playerid][pIP]), "%s", ip);

    new message[144];
    format(message, sizeof(message), "Witaj %s na %s v%s", name, SERVER_NAME, SERVER_VERSION);
    SendClientMessage(playerid, COLOR_INFO, message);

    Players_LoadAccount(playerid);
    TogglePlayerSpectating(playerid, true);
    Players_ShowLoginDialog(playerid);
    return 1;
}

stock Players_OnPlayerDisconnect(playerid, reason)
{
    if(PlayerData[playerid][pLogged])
    {
        Players_SaveAccount(playerid);
    }
    Core_ResetPlayerData(playerid);
    return 1;
}

stock Players_OnPlayerRequestClass(playerid, classid)
{
    SetPlayerInterior(playerid, 0);
    SetPlayerVirtualWorld(playerid, playerid + 1);
    SetPlayerPos(playerid, 1958.3783, 1343.1572, 15.3746);
    SetPlayerCameraPos(playerid, 1958.3783, 1348.1572, 17.8746);
    SetPlayerCameraLookAt(playerid, 1958.3783, 1343.1572, 15.3746);
    return 1;
}

stock Players_OnPlayerSpawn(playerid)
{
    if(!PlayerData[playerid][pLogged])
    {
        Players_ShowLoginDialog(playerid);
        return 0;
    }
    Players_SpawnPlayer(playerid);
    return 1;
}

stock Players_OnPlayerCommandText(playerid, cmdtext[])
{
    if(!PlayerData[playerid][pLogged])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Musisz byc zalogowany aby korzystac z komend.");
        return 1;
    }

    if(!strcmp(cmdtext, "/stats", true))
    {
        new message[256];
        format(message, sizeof(message), "Poziom: %d | Gotowka: %d$ | Skin: %d", PlayerData[playerid][pLevel], PlayerData[playerid][pMoney], PlayerData[playerid][pSkin]);
        SendClientMessage(playerid, COLOR_INFO, message);
        format(message, sizeof(message), "Ostatnie logowanie: %s | IP: %s", PlayerData[playerid][pLastLogin], PlayerData[playerid][pIP]);
        SendClientMessage(playerid, COLOR_INFO, message);
        return 1;
    }

    if(!strcmp(cmdtext, "/changepass", true))
    {
        ShowPlayerDialog(playerid, DIALOG_CHANGEPASS, DIALOG_STYLE_PASSWORD, "Zmiana hasla", "Podaj nowe haslo do konta", "Zapisz", "Anuluj");
        return 1;
    }

    if(!strcmp(cmdtext, "/logout", true))
    {
        Players_SaveAccount(playerid);
        SendClientMessage(playerid, COLOR_WARNING, "Wylogowales sie z konta.");
        TogglePlayerSpectating(playerid, true);
        PlayerData[playerid][pLogged] = false;
        Players_ShowLoginDialog(playerid);
        return 1;
    }

    return 0;
}

stock Players_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[])
{
    switch(dialogid)
    {
        case DIALOG_LOGIN:
        {
            if(!response)
            {
                Kick(playerid);
                return 1;
            }
            if(strlen(inputtext) < 4)
            {
                SendClientMessage(playerid, COLOR_ERROR, "Haslo musi posiadac co najmniej 4 znaki.");
                Players_ShowLoginDialog(playerid);
                return 1;
            }
            Players_LoginPlayer(playerid, inputtext);
            return 1;
        }
        case DIALOG_REGISTER:
        {
            if(!response)
            {
                Kick(playerid);
                return 1;
            }
            if(strlen(inputtext) < 6)
            {
                SendClientMessage(playerid, COLOR_ERROR, "Haslo musi posiadac co najmniej 6 znakow.");
                Players_ShowRegisterDialog(playerid);
                return 1;
            }
            Players_RegisterPlayer(playerid, inputtext);
            return 1;
        }
        case DIALOG_CHANGEPASS:
        {
            if(!response)
            {
                return 1;
            }
            if(strlen(inputtext) < 6)
            {
                SendClientMessage(playerid, COLOR_ERROR, "Haslo musi posiadac co najmniej 6 znakow.");
                return 1;
            }

            new salt[MAX_ACCOUNT_SALT + 1];
            Players_GenerateSalt(salt, sizeof(salt));

            new hashed[129];
            new saltedPassword[128];
            format(saltedPassword, sizeof(saltedPassword), "%s%s", inputtext, salt);
            WP_Hash(hashed, saltedPassword);

            new name[MAX_PLAYER_NAME + 1];
            GetPlayerName(playerid, name, sizeof(name));

            new query[512];
            format(query, sizeof(query), "UPDATE accounts SET password='%s', salt='%s' WHERE id=%d", hashed, salt, PlayerData[playerid][pID]);
            Database_Execute(query);

            format(PlayerData[playerid][pPassword], sizeof(PlayerData[playerid][pPassword]), "%s", hashed);
            format(PlayerData[playerid][pSalt], sizeof(PlayerData[playerid][pSalt]), "%s", salt);

            SendClientMessage(playerid, COLOR_SUCCESS, "Haslo zostalo pomyslnie zmienione.");

            new logMessage[144];
            format(logMessage, sizeof(logMessage), "Zmienil haslo na koncie.");
            Players_LogEvent(playerid, "SECURITY", logMessage);
            return 1;
        }
    }
    return 0;
}

stock Players_OnPlayerStateChange(playerid, newstate, oldstate)
{
    if(newstate == PLAYER_STATE_DRIVER)
    {
        Players_UpdateSession(playerid);
    }
    return 1;
}

stock Players_SaveAccount(playerid)
{
    if(!PlayerData[playerid][pLogged])
    {
        return 0;
    }

    Players_UpdateSession(playerid);
    PlayerData[playerid][pMoney] = GetPlayerMoney(playerid);
    PlayerData[playerid][pSkin] = GetPlayerSkin(playerid);

    new query[512];
    format(query, sizeof(query), "UPDATE accounts SET level=%d, money=%d, skin=%d, spawn_x=%f, spawn_y=%f, spawn_z=%f, spawn_angle=%f, last_login='%s' WHERE id=%d",
        PlayerData[playerid][pLevel], PlayerData[playerid][pMoney], PlayerData[playerid][pSkin],
        Float:PlayerData[playerid][pSpawnX], Float:PlayerData[playerid][pSpawnY], Float:PlayerData[playerid][pSpawnZ],
        Float:PlayerData[playerid][pSpawnAngle], PlayerData[playerid][pLastLogin], PlayerData[playerid][pID]);
    Database_Execute(query);

    new logMessage[144];
    format(logMessage, sizeof(logMessage), "Zapisano dane konta.");
    Players_LogEvent(playerid, "INFO", logMessage);
    return 1;
}

stock Players_LoadAccount(playerid)
{
    new name[MAX_PLAYER_NAME + 1];
    GetPlayerName(playerid, name, sizeof(name));

    new escapedName[2 * MAX_PLAYER_NAME + 1];
    Database_Escape(name, escapedName, sizeof(escapedName));

    new query[256];
    format(query, sizeof(query), "SELECT * FROM accounts WHERE name='%s'", escapedName);

    new DBResult:result = db_query(gDatabaseHandle, query);
    if(!result)
    {
        return 0;
    }

    if(db_num_rows(result) > 0)
    {
        PlayerData[playerid][pRegistered] = true;
        db_next_row(result);

        PlayerData[playerid][pID] = Database_FetchInt(result, "id");
        PlayerData[playerid][pLevel] = Database_FetchInt(result, "level");
        PlayerData[playerid][pMoney] = Database_FetchInt(result, "money");
        PlayerData[playerid][pSkin] = Database_FetchInt(result, "skin");

        new Float:spawnX = Database_FetchFloat(result, "spawn_x");
        new Float:spawnY = Database_FetchFloat(result, "spawn_y");
        new Float:spawnZ = Database_FetchFloat(result, "spawn_z");
        new Float:spawnA = Database_FetchFloat(result, "spawn_angle");

        PlayerData[playerid][pSpawnX] = spawnX;
        PlayerData[playerid][pSpawnY] = spawnY;
        PlayerData[playerid][pSpawnZ] = spawnZ;
        PlayerData[playerid][pSpawnAngle] = spawnA;
        Database_FetchString(result, "password", PlayerData[playerid][pPassword], sizeof(PlayerData[playerid][pPassword]));
        Database_FetchString(result, "salt", PlayerData[playerid][pSalt], sizeof(PlayerData[playerid][pSalt]));
        Database_FetchString(result, "last_login", PlayerData[playerid][pLastLogin], sizeof(PlayerData[playerid][pLastLogin]));

        new ip[16];
        GetPlayerIp(playerid, ip, sizeof(ip));
        new escapedIP[33];
        Database_Escape(ip, escapedIP, sizeof(escapedIP));

        format(query, sizeof(query), "UPDATE accounts SET ip='%s' WHERE id=%d", escapedIP, PlayerData[playerid][pID]);
        Database_Execute(query);
    }
    else
    {
        PlayerData[playerid][pRegistered] = false;
    }

    db_free_result(result);
    return 1;
}

stock Players_LoginPlayer(playerid, const password[])
{
    if(!PlayerData[playerid][pRegistered])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Twoje konto nie istnieje. Zarejestruj sie.");
        Players_ShowRegisterDialog(playerid);
        return 1;
    }

    if(PlayerData[playerid][pLoginAttempts] >= MAX_LOGIN_ATTEMPTS)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Przekroczono limit prob logowania. Polaczenie zostanie rozlaczone.");
        Kick(playerid);
        return 1;
    }

    new saltedPassword[128];
    format(saltedPassword, sizeof(saltedPassword), "%s%s", password, PlayerData[playerid][pSalt]);

    new hashed[129];
    WP_Hash(hashed, saltedPassword);

    if(strcmp(hashed, PlayerData[playerid][pPassword], false) != 0)
    {
        PlayerData[playerid][pLoginAttempts]++;
        SendClientMessage(playerid, COLOR_ERROR, "Niepoprawne haslo. Sprobuj ponownie.");
        Players_ShowLoginDialog(playerid);
        return 1;
    }

    PlayerData[playerid][pLogged] = true;
    PlayerData[playerid][pSessionStart] = gettime();

    GivePlayerMoney(playerid, PlayerData[playerid][pMoney] - GetPlayerMoney(playerid));
    SetSpawnInfo(playerid, 0, PlayerData[playerid][pSkin], Float:PlayerData[playerid][pSpawnX], Float:PlayerData[playerid][pSpawnY], Float:PlayerData[playerid][pSpawnZ], Float:PlayerData[playerid][pSpawnAngle], 0, 0, 0, 0, 0, 0);
    TogglePlayerSpectating(playerid, false);
    SpawnPlayer(playerid);

    new message[144];
    format(message, sizeof(message), "Zalogowales sie pomyslnie. Zycze milej gry!");
    SendClientMessage(playerid, COLOR_SUCCESS, message);

    new timestamp[32];
    Core_FormatTime(timestamp, sizeof(timestamp));
    format(PlayerData[playerid][pLastLogin], sizeof(PlayerData[playerid][pLastLogin]), "%s", timestamp);

    new logMessage[144];
    format(logMessage, sizeof(logMessage), "Zalogowal sie na serwer.");
    Players_LogEvent(playerid, "LOGIN", logMessage);
    return 1;
}

stock Players_RegisterPlayer(playerid, const password[])
{
    if(PlayerData[playerid][pRegistered])
    {
        SendClientMessage(playerid, COLOR_WARNING, "Konto juz istnieje. Zaloguj sie.");
        Players_ShowLoginDialog(playerid);
        return 1;
    }

    new salt[MAX_ACCOUNT_SALT + 1];
    Players_GenerateSalt(salt, sizeof(salt));

    new saltedPassword[128];
    format(saltedPassword, sizeof(saltedPassword), "%s%s", password, salt);

    new hashed[129];
    WP_Hash(hashed, saltedPassword);

    new name[MAX_PLAYER_NAME + 1];
    GetPlayerName(playerid, name, sizeof(name));

    new escapedName[2 * MAX_PLAYER_NAME + 1];
    Database_Escape(name, escapedName, sizeof(escapedName));

    new ip[16];
    GetPlayerIp(playerid, ip, sizeof(ip));
    new escapedIP[33];
    Database_Escape(ip, escapedIP, sizeof(escapedIP));

    new query[512];
    format(query, sizeof(query),
        "INSERT INTO accounts (name, password, salt, level, money, skin, spawn_x, spawn_y, spawn_z, spawn_angle, ip, last_login) VALUES ('%s', '%s', '%s', %d, %d, %d, %f, %f, %f, %f, '%s', CURRENT_TIMESTAMP)",
        escapedName, hashed, salt, PlayerData[playerid][pLevel], PlayerData[playerid][pMoney], PlayerData[playerid][pSkin],
        Float:PlayerData[playerid][pSpawnX], Float:PlayerData[playerid][pSpawnY], Float:PlayerData[playerid][pSpawnZ], Float:PlayerData[playerid][pSpawnAngle], escapedIP);

    Database_Execute(query);

    PlayerData[playerid][pID] = db_last_insert_rowid(gDatabaseHandle);
    PlayerData[playerid][pRegistered] = true;
    format(PlayerData[playerid][pPassword], sizeof(PlayerData[playerid][pPassword]), "%s", hashed);
    format(PlayerData[playerid][pSalt], sizeof(PlayerData[playerid][pSalt]), "%s", salt);

    SendClientMessage(playerid, COLOR_SUCCESS, "Rejestracja przebiegla pomyslnie. Zaloguj sie.");
    Players_ShowLoginDialog(playerid);

    new logMessage[144];
    format(logMessage, sizeof(logMessage), "Zarejestrowal nowe konto.");
    Players_LogEvent(playerid, "REGISTER", logMessage);
    return 1;
}

stock Players_ShowLoginDialog(playerid)
{
    if(PlayerData[playerid][pRegistered])
    {
        ShowPlayerDialog(playerid, DIALOG_LOGIN, DIALOG_STYLE_PASSWORD, "Logowanie", "Podaj haslo aby sie zalogowac", "Zaloguj", "Wyjdz");
    }
    else
    {
        Players_ShowRegisterDialog(playerid);
    }
    return 1;
}

stock Players_ShowRegisterDialog(playerid)
{
    ShowPlayerDialog(playerid, DIALOG_REGISTER, DIALOG_STYLE_PASSWORD, "Rejestracja", "Podaj haslo aby utworzyc konto", "Zarejestruj", "Wyjdz");
    return 1;
}

stock Players_SpawnPlayer(playerid)
{
    SetPlayerInterior(playerid, 0);
    SetPlayerVirtualWorld(playerid, 0);
    SetPlayerPos(playerid, Float:PlayerData[playerid][pSpawnX], Float:PlayerData[playerid][pSpawnY], Float:PlayerData[playerid][pSpawnZ]);
    SetPlayerFacingAngle(playerid, Float:PlayerData[playerid][pSpawnAngle]);
    SetCameraBehindPlayer(playerid);
    PlayerData[playerid][pSpawnPrepared] = true;
    return 1;
}

stock Players_UpdateSession(playerid)
{
    if(!PlayerData[playerid][pLogged])
    {
        return 0;
    }
    new now = gettime();
    new played = now - PlayerData[playerid][pSessionStart];
    if(played < 0) played = 0;
    PlayerData[playerid][pPlayTime] += played;
    PlayerData[playerid][pSessionStart] = now;
    return 1;
}

stock Players_GenerateSalt(output[], length)
{
    static const characters[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    new charCount = sizeof(characters) - 1;
    for(new i = 0; i < length - 1; i++)
    {
        output[i] = characters[random(charCount)];
    }
    output[length - 1] = '\0';
    return 1;
}

stock Players_LogEvent(playerid, const level[], const message[])
{
    new name[MAX_PLAYER_NAME + 1];
    GetPlayerName(playerid, name, sizeof(name));

    new escapedName[2 * MAX_PLAYER_NAME + 1];
    Database_Escape(name, escapedName, sizeof(escapedName));

    new escapedMessage[256];
    Database_Escape(message, escapedMessage, sizeof(escapedMessage));

    new query[256];
    format(query, sizeof(query), "INSERT INTO server_logs (level, message) VALUES ('%s', '[%s] %s')", level, escapedName, escapedMessage);
    Database_Execute(query);
    return 1;
}

