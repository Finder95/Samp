#if defined _ADMIN_MODULE_INCLUDED
    #endinput
#endif
#define _ADMIN_MODULE_INCLUDED

#define ADMIN_CHAT_PREFIX "[ADMIN]"

forward Admin_Init();
forward Admin_Shutdown();
forward Admin_OnPlayerCommandText(playerid, cmdtext[]);
forward Admin_OnRconCommand(cmd[]);
forward Admin_IsPlayerAuthorized(playerid, level);
forward Admin_LogAction(playerid, const action[]);
forward Admin_Broadcast(const message[]);

stock Admin_Init()
{
    Core_Log("[Admin] Moduly administracyjne gotowe.");
    return 1;
}

stock Admin_Shutdown()
{
    Core_Log("[Admin] Moduly administracyjne zamkniete.");
    return 1;
}

stock Admin_OnPlayerCommandText(playerid, cmdtext[])
{
    if(!PlayerData[playerid][pLogged])
    {
        return 0;
    }

    new command[32], params[192];
    sscanf(cmdtext, "s[32]S()[192]", command, params);

    if(!strcmp(command, "/a", true))
    {
        if(!Admin_IsPlayerAuthorized(playerid, 2))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Brak uprawnien administracyjnych.");
            return 1;
        }

        if(!params[0])
        {
            SendClientMessage(playerid, COLOR_WARNING, "Uzycie: /a <wiadomosc>");
            return 1;
        }

        new name[MAX_PLAYER_NAME + 1];
        GetPlayerName(playerid, name, sizeof(name));

        new message[192];
        format(message, sizeof(message), "%s %s: %s", ADMIN_CHAT_PREFIX, name, params);

        for(new i = 0; i < MAX_PLAYERS; i++)
        {
            if(IsPlayerConnected(i) && PlayerData[i][pLogged] && Admin_IsPlayerAuthorized(i, 2))
            {
                SendClientMessage(i, COLOR_ADMIN, message);
            }
        }

        Admin_LogAction(playerid, "Wyslal wiadomosc na czacie administracyjnym.");
        return 1;
    }

    if(!strcmp(command, "/setlevel", true))
    {
        if(!Admin_IsPlayerAuthorized(playerid, 3))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Brak uprawnien do zmiany poziomu.");
            return 1;
        }

        new targetid, level;
        if(sscanf(params, "dd", targetid, level))
        {
            SendClientMessage(playerid, COLOR_WARNING, "Uzycie: /setlevel <id> <poziom>");
            return 1;
        }

        if(!IsPlayerConnected(targetid))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Wybrany gracz nie jest polaczony.");
            return 1;
        }

        PlayerData[targetid][pLevel] = level;

        new query[128];
        format(query, sizeof(query), "UPDATE accounts SET level=%d WHERE id=%d", level, PlayerData[targetid][pID]);
        Database_Execute(query);

        new name[MAX_PLAYER_NAME + 1];
        GetPlayerName(targetid, name, sizeof(name));

        new info[160];
        format(info, sizeof(info), "Ustawiles poziom gracza %s na %d.", name, level);
        SendClientMessage(playerid, COLOR_SUCCESS, info);

        format(info, sizeof(info), "Administrator ustawil Twoj poziom na %d.", level);
        SendClientMessage(targetid, COLOR_WARNING, info);

        Admin_LogAction(playerid, "Zmiana poziomu gracza.");
        return 1;
    }

    if(!strcmp(command, "/kick", true))
    {
        if(!Admin_IsPlayerAuthorized(playerid, 2))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Brak uprawnien do wyrzucania graczy.");
            return 1;
        }

        new targetid;
        if(sscanf(params, "d", targetid))
        {
            SendClientMessage(playerid, COLOR_WARNING, "Uzycie: /kick <id>");
            return 1;
        }

        if(!IsPlayerConnected(targetid))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Wybrany gracz nie jest polaczony.");
            return 1;
        }

        new name[MAX_PLAYER_NAME + 1];
        GetPlayerName(targetid, name, sizeof(name));

        Kick(targetid);

        new message[144];
        format(message, sizeof(message), "Gracz %s zostal wyrzucony z serwera.", name);
        SendClientMessageToAll(COLOR_WARNING, message);

        Admin_LogAction(playerid, "Wyrzucil gracza z serwera.");
        return 1;
    }

    if(!strcmp(command, "/announce", true))
    {
        if(!Admin_IsPlayerAuthorized(playerid, 2))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Brak uprawnien do ogloszen.");
            return 1;
        }

        if(!params[0])
        {
            SendClientMessage(playerid, COLOR_WARNING, "Uzycie: /announce <wiadomosc>");
            return 1;
        }

        new message[220];
        format(message, sizeof(message), "[OGL] %s", params);
        Admin_Broadcast(message);

        Admin_LogAction(playerid, "Wyslal ogloszenie globalne.");
        return 1;
    }

    return 0;
}

stock Admin_OnRconCommand(cmd[])
{
    new lowered[64];
    format(lowered, sizeof(lowered), "%s", cmd);
    strlower(lowered);

    if(!strcmp(lowered, "reloadadmins", true))
    {
        Core_Log("[Admin] Przeladowanie listy administratorow nie jest wymagane w tym trybie.");
        return 1;
    }
    return 0;
}

stock Admin_IsPlayerAuthorized(playerid, level)
{
    if(!PlayerData[playerid][pLogged])
    {
        return 0;
    }
    return PlayerData[playerid][pLevel] >= level;
}

stock Admin_LogAction(playerid, const action[])
{
    new name[MAX_PLAYER_NAME + 1];
    GetPlayerName(playerid, name, sizeof(name));

    new escapedName[2 * MAX_PLAYER_NAME + 1];
    Database_Escape(name, escapedName, sizeof(escapedName));

    new escapedAction[256];
    Database_Escape(action, escapedAction, sizeof(escapedAction));

    new query[256];
    format(query, sizeof(query), "INSERT INTO admin_logs (admin_name, action) VALUES ('%s', '%s')", escapedName, escapedAction);
    Database_Execute(query);
    return 1;
}

stock Admin_Broadcast(const message[])
{
    for(new i = 0; i < MAX_PLAYERS; i++)
    {
        if(IsPlayerConnected(i))
        {
            GameTextForPlayer(i, message, 4000, 3);
            SendClientMessage(i, COLOR_INFO, message);
        }
    }
    return 1;
}

