#if defined _PROPERTIES_MODULE_INCLUDED
    #endinput
#endif
#define _PROPERTIES_MODULE_INCLUDED

#define MAX_PROPERTIES 64
#define PROPERTY_INTERACTION_RANGE 3.5
#define PROPERTY_VIRTUAL_BASE 2000

#define DIALOG_PROPERTY_MENU 1800
#define DIALOG_PROPERTY_CONFIRM 1801

enum E_PROPERTY_DATA
{
    prSQLID,
    prName[64],
    prPrice,
    prOwnerID,
    prOwnerName[MAX_PLAYER_NAME + 1],
    prLocked,
    prInterior,
    Float:prEnterX,
    Float:prEnterY,
    Float:prEnterZ,
    Float:prExitX,
    Float:prExitY,
    Float:prExitZ,
    prPickup,
    prExitPickup,
    Text3D:prLabel,
    Text3D:prExitLabel,
    prVirtualWorld
};

enum E_PROPERTY_OPTION
{
    PROPERTY_OPTION_NONE,
    PROPERTY_OPTION_ENTER,
    PROPERTY_OPTION_PREVIEW,
    PROPERTY_OPTION_BUY,
    PROPERTY_OPTION_SELL,
    PROPERTY_OPTION_TOGGLE_LOCK,
    PROPERTY_OPTION_SET_SPAWN
};

new PropertyData[MAX_PROPERTIES][E_PROPERTY_DATA];
new PropertyCount = 0;

new PropertyDialogOptions[MAX_PLAYERS][8];
new PropertyDialogOptionCount[MAX_PLAYERS];
new PropertyDialogPendingAction[MAX_PLAYERS];
new PlayerPropertyTarget[MAX_PLAYERS];
new PlayerPropertyInside[MAX_PLAYERS];

forward Properties_Init();
forward Properties_Shutdown();
forward Properties_OnPlayerConnect(playerid);
forward Properties_OnPlayerDisconnect(playerid);
forward Properties_OnAccountLoaded(playerid);
forward Properties_OnAccountRegistered(playerid);
forward Properties_OnPlayerLogin(playerid);
forward Properties_OnPlayerSpawn(playerid);
forward Properties_OnPlayerCommandText(playerid, cmdtext[]);
forward Properties_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[]);
forward Properties_OnPlayerSave(playerid);
forward Properties_OnPlayerPickUpPickup(playerid, pickupid);
forward Properties_GetPropertyName(sqlid, output[], size);

stock Properties_Init()
{
    for(new i = 0; i < MAX_PROPERTIES; i++)
    {
        Properties_ResetProperty(i);
    }

    for(new playerid = 0; playerid < MAX_PLAYERS; playerid++)
    {
        Properties_ResetPlayer(playerid);
    }

    PropertyCount = 0;
    Properties_SeedDefaults();
    Properties_LoadAll();

    Core_Log("[Properties] Modul nieruchomosci zostal zainicjalizowany.");
    return 1;
}

stock Properties_Shutdown()
{
    for(new i = 0; i < PropertyCount; i++)
    {
        Properties_DestroyVisual(i);
    }
    PropertyCount = 0;
    Core_Log("[Properties] Modul nieruchomosci zostal zamkniety.");
    return 1;
}

stock Properties_OnPlayerConnect(playerid)
{
    Properties_ResetPlayer(playerid);
    return 1;
}

stock Properties_OnPlayerDisconnect(playerid)
{
    Properties_ResetPlayer(playerid);
    return 1;
}

stock Properties_OnAccountLoaded(playerid)
{
    if(PlayerData[playerid][pPropertyID] <= 0)
    {
        return 1;
    }

    new index = Properties_FindBySQLID(PlayerData[playerid][pPropertyID]);
    if(index != -1)
    {
        PropertyData[index][prOwnerID] = PlayerData[playerid][pID];
        GetPlayerName(playerid, PropertyData[index][prOwnerName], sizeof(PropertyData[index][prOwnerName]));
        Properties_RefreshVisual(index);
    }
    return 1;
}

stock Properties_OnAccountRegistered(playerid)
{
    PlayerData[playerid][pPropertyID] = 0;
    PlayerData[playerid][pPropertySpawn] = false;
    return 1;
}

stock Properties_OnPlayerLogin(playerid)
{
    if(PlayerData[playerid][pPropertyID] > 0)
    {
        new index = Properties_FindBySQLID(PlayerData[playerid][pPropertyID]);
        if(index != -1)
        {
            GetPlayerName(playerid, PropertyData[index][prOwnerName], sizeof(PropertyData[index][prOwnerName]));
            PropertyData[index][prOwnerID] = PlayerData[playerid][pID];
            Properties_RefreshVisual(index);

            new message[144];
            format(message, sizeof(message), "Twoj dom: %s | Status drzwi: %s", PropertyData[index][prName], PropertyData[index][prLocked] ? "Zamkniete" : "Otwarte");
            SendClientMessage(playerid, COLOR_INFO, message);
        }
        else
        {
            PlayerData[playerid][pPropertyID] = 0;
            PlayerData[playerid][pPropertySpawn] = false;
        }
    }
    return 1;
}

stock Properties_OnPlayerSpawn(playerid)
{
    if(!PlayerData[playerid][pPropertySpawn])
    {
        return 1;
    }

    if(PlayerData[playerid][pPropertyID] <= 0)
    {
        PlayerData[playerid][pPropertySpawn] = false;
        return 1;
    }

    new index = Properties_FindBySQLID(PlayerData[playerid][pPropertyID]);
    if(index == -1)
    {
        PlayerData[playerid][pPropertySpawn] = false;
        return 1;
    }

    SetPlayerInterior(playerid, PropertyData[index][prInterior]);
    SetPlayerVirtualWorld(playerid, PropertyData[index][prVirtualWorld]);
    SetPlayerPos(playerid, Float:PropertyData[index][prExitX], Float:PropertyData[index][prExitY], Float:PropertyData[index][prExitZ]);
    SetCameraBehindPlayer(playerid);
    PlayerPropertyInside[playerid] = index;
    PlayerPropertyTarget[playerid] = index;

    new message[128];
    format(message, sizeof(message), "Zrespawnowales w swoim domu: %s", PropertyData[index][prName]);
    SendClientMessage(playerid, COLOR_INFO, message);
    return 1;
}

stock Properties_OnPlayerCommandText(playerid, cmdtext[])
{
    if(!strcmp(cmdtext, "/dom", true))
    {
        new index = PlayerPropertyTarget[playerid];
        if(index == -1)
        {
            index = Properties_FindNearest(playerid, PROPERTY_INTERACTION_RANGE);
        }

        if(index == -1)
        {
            SendClientMessage(playerid, COLOR_ERROR, "Nie ma nieruchomosci w poblizu.");
            return 1;
        }

        PlayerPropertyTarget[playerid] = index;
        Properties_ShowMenu(playerid, index);
        return 1;
    }

    if(!strcmp(cmdtext, "/wyjdz", true))
    {
        if(PlayerPropertyInside[playerid] == -1)
        {
            SendClientMessage(playerid, COLOR_WARNING, "Nie znajdujesz sie w zadnej nieruchomosci.");
            return 1;
        }

        Properties_Exit(playerid, PlayerPropertyInside[playerid]);
        return 1;
    }

    if(!strcmp(cmdtext, "/kupdom", true))
    {
        new index = PlayerPropertyTarget[playerid];
        if(index == -1)
        {
            index = Properties_FindNearest(playerid, PROPERTY_INTERACTION_RANGE);
        }

        if(index == -1)
        {
            SendClientMessage(playerid, COLOR_ERROR, "Nie ma nieruchomosci w poblizu.");
            return 1;
        }

        Properties_AttemptBuy(playerid, index);
        return 1;
    }

    return 0;
}

stock Properties_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[])
{
    switch(dialogid)
    {
        case DIALOG_PROPERTY_MENU:
        {
            if(!response)
            {
                return 1;
            }

            if(listitem < 0 || listitem >= PropertyDialogOptionCount[playerid])
            {
                return 1;
            }

            new action = PropertyDialogOptions[playerid][listitem];
            PropertyDialogPendingAction[playerid] = action;

            switch(action)
            {
                case PROPERTY_OPTION_BUY:
                {
                    Properties_ShowConfirm(playerid, "Czy na pewno chcesz kupic ten dom? Koszt zostanie pobrany z gotowki.");
                    return 1;
                }
                case PROPERTY_OPTION_SELL:
                {
                    Properties_ShowConfirm(playerid, "Czy na pewno chcesz sprzedac dom? Otrzymasz 70 procent jego wartosci.");
                    return 1;
                }
                default:
                {
                    Properties_ExecuteAction(playerid, action);
                }
            }
            return 1;
        }
        case DIALOG_PROPERTY_CONFIRM:
        {
            if(response)
            {
                Properties_ExecuteAction(playerid, PropertyDialogPendingAction[playerid]);
            }
            PropertyDialogPendingAction[playerid] = PROPERTY_OPTION_NONE;
            return 1;
        }
    }
    return 0;
}

stock Properties_OnPlayerSave(playerid)
{
    return 1;
}

stock Properties_OnPlayerPickUpPickup(playerid, pickupid)
{
    for(new i = 0; i < PropertyCount; i++)
    {
        if(PropertyData[i][prPickup] == pickupid)
        {
            PlayerPropertyTarget[playerid] = i;
            Properties_ShowHint(playerid, i);
            return 1;
        }

        if(PropertyData[i][prExitPickup] == pickupid && PlayerPropertyInside[playerid] == i)
        {
            Properties_Exit(playerid, i);
            return 1;
        }
    }
    return 0;
}

stock Properties_ResetProperty(index)
{
    PropertyData[index][prSQLID] = 0;
    PropertyData[index][prName][0] = '\0';
    PropertyData[index][prPrice] = 0;
    PropertyData[index][prOwnerID] = 0;
    PropertyData[index][prOwnerName][0] = '\0';
    PropertyData[index][prLocked] = 0;
    PropertyData[index][prInterior] = 0;
    PropertyData[index][prEnterX] = 0.0;
    PropertyData[index][prEnterY] = 0.0;
    PropertyData[index][prEnterZ] = 0.0;
    PropertyData[index][prExitX] = 0.0;
    PropertyData[index][prExitY] = 0.0;
    PropertyData[index][prExitZ] = 0.0;
    PropertyData[index][prPickup] = -1;
    PropertyData[index][prExitPickup] = -1;
    PropertyData[index][prLabel] = Text3D:INVALID_3DTEXT_ID;
    PropertyData[index][prExitLabel] = Text3D:INVALID_3DTEXT_ID;
    PropertyData[index][prVirtualWorld] = 0;
}

stock Properties_ResetPlayer(playerid)
{
    PlayerPropertyTarget[playerid] = -1;
    PlayerPropertyInside[playerid] = -1;
    PropertyDialogOptionCount[playerid] = 0;
    PropertyDialogPendingAction[playerid] = PROPERTY_OPTION_NONE;
    for(new i = 0; i < sizeof(PropertyDialogOptions[]); i++)
    {
        PropertyDialogOptions[playerid][i] = PROPERTY_OPTION_NONE;
    }
    return 1;
}

stock Properties_LoadAll()
{
    new query[256];
    format(query, sizeof(query), "SELECT p.*, IFNULL(a.name, '') AS owner_name FROM properties p LEFT JOIN accounts a ON a.id = p.owner_id ORDER BY p.id ASC");

    new DBResult:result = db_query(gDatabaseHandle, query);
    if(!result)
    {
        return 0;
    }

    while(db_next_row(result))
    {
        if(PropertyCount >= MAX_PROPERTIES)
        {
            break;
        }

        new index = PropertyCount++;
        PropertyData[index][prSQLID] = Database_FetchInt(result, "id");
        Database_FetchString(result, "name", PropertyData[index][prName], sizeof(PropertyData[index][prName]));
        Database_FetchString(result, "owner_name", PropertyData[index][prOwnerName], sizeof(PropertyData[index][prOwnerName]));
        PropertyData[index][prPrice] = Database_FetchInt(result, "price");
        PropertyData[index][prOwnerID] = Database_FetchInt(result, "owner_id");
        PropertyData[index][prLocked] = Database_FetchInt(result, "locked");
        PropertyData[index][prInterior] = Database_FetchInt(result, "interior");
        PropertyData[index][prEnterX] = Database_FetchFloat(result, "enter_x");
        PropertyData[index][prEnterY] = Database_FetchFloat(result, "enter_y");
        PropertyData[index][prEnterZ] = Database_FetchFloat(result, "enter_z");
        PropertyData[index][prExitX] = Database_FetchFloat(result, "exit_x");
        PropertyData[index][prExitY] = Database_FetchFloat(result, "exit_y");
        PropertyData[index][prExitZ] = Database_FetchFloat(result, "exit_z");

        if(PropertyData[index][prOwnerID] == 0)
        {
            PropertyData[index][prLocked] = 0;
            format(PropertyData[index][prOwnerName], sizeof(PropertyData[index][prOwnerName]), "Brak");
        }

        PropertyData[index][prVirtualWorld] = PROPERTY_VIRTUAL_BASE + PropertyData[index][prSQLID];
        Properties_CreateVisual(index);
        Properties_RefreshVisual(index);
    }

    db_free_result(result);
    return 1;
}

stock Properties_CreateVisual(index)
{
    if(PropertyData[index][prPickup] != -1)
    {
        DestroyPickup(PropertyData[index][prPickup]);
    }
    if(PropertyData[index][prLabel] != Text3D:INVALID_3DTEXT_ID)
    {
        Delete3DTextLabel(PropertyData[index][prLabel]);
    }
    if(PropertyData[index][prExitPickup] != -1)
    {
        DestroyPickup(PropertyData[index][prExitPickup]);
    }
    if(PropertyData[index][prExitLabel] != Text3D:INVALID_3DTEXT_ID)
    {
        Delete3DTextLabel(PropertyData[index][prExitLabel]);
    }

    PropertyData[index][prPickup] = CreatePickup(1273, 23, Float:PropertyData[index][prEnterX], Float:PropertyData[index][prEnterY], Float:PropertyData[index][prEnterZ]);
    PropertyData[index][prLabel] = Create3DTextLabel("", COLOR_WHITE, Float:PropertyData[index][prEnterX], Float:PropertyData[index][prEnterY], Float:PropertyData[index][prEnterZ] + 1.0, 30.0, 0, 0);

    PropertyData[index][prExitPickup] = CreatePickup(19132, 1, Float:PropertyData[index][prExitX], Float:PropertyData[index][prExitY], Float:PropertyData[index][prExitZ], PropertyData[index][prVirtualWorld]);
    PropertyData[index][prExitLabel] = Create3DTextLabel("Wyjscie\nUzyj /wyjdz", COLOR_WHITE, Float:PropertyData[index][prExitX], Float:PropertyData[index][prExitY], Float:PropertyData[index][prExitZ] + 0.8, 25.0, PropertyData[index][prVirtualWorld], 0);
    return 1;
}

stock Properties_DestroyVisual(index)
{
    if(PropertyData[index][prPickup] != -1)
    {
        DestroyPickup(PropertyData[index][prPickup]);
        PropertyData[index][prPickup] = -1;
    }
    if(PropertyData[index][prLabel] != Text3D:INVALID_3DTEXT_ID)
    {
        Delete3DTextLabel(PropertyData[index][prLabel]);
        PropertyData[index][prLabel] = Text3D:INVALID_3DTEXT_ID;
    }
    if(PropertyData[index][prExitPickup] != -1)
    {
        DestroyPickup(PropertyData[index][prExitPickup]);
        PropertyData[index][prExitPickup] = -1;
    }
    if(PropertyData[index][prExitLabel] != Text3D:INVALID_3DTEXT_ID)
    {
        Delete3DTextLabel(PropertyData[index][prExitLabel]);
        PropertyData[index][prExitLabel] = Text3D:INVALID_3DTEXT_ID;
    }
    return 1;
}

stock Properties_RefreshVisual(index)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    new status[64];
    if(PropertyData[index][prOwnerID] == 0)
    {
        format(status, sizeof(status), "Status: Na sprzedaz");
    }
    else
    {
        format(status, sizeof(status), "Wlasciciel: %s", PropertyData[index][prOwnerName]);
    }

    new lockStatus[64];
    format(lockStatus, sizeof(lockStatus), "Drzwi: %s", PropertyData[index][prLocked] ? "Zamkniete" : "Otwarte");

    new label[256];
    format(label, sizeof(label), "%s\nCena: %d$\n%s\n%s\nKomenda: /dom", PropertyData[index][prName], PropertyData[index][prPrice], status, lockStatus);

    Update3DTextLabelText(PropertyData[index][prLabel], COLOR_INFO, label);
    return 1;
}

stock Properties_ShowMenu(playerid, propertyIndex)
{
    PropertyDialogOptionCount[playerid] = 0;
    PlayerPropertyTarget[playerid] = propertyIndex;
    for(new i = 0; i < sizeof(PropertyDialogOptions[]); i++)
    {
        PropertyDialogOptions[playerid][i] = PROPERTY_OPTION_NONE;
    }

    new info[256];
    format(info, sizeof(info), "%s - cena %d$, drzwi %s", PropertyData[propertyIndex][prName], PropertyData[propertyIndex][prPrice], PropertyData[propertyIndex][prLocked] ? "zamkniete" : "otwarte");
    SendClientMessage(playerid, COLOR_INFO, info);

    new options[512];
    options[0] = '\0';

    if(PropertyData[propertyIndex][prOwnerID] == 0)
    {
        Properties_AddOption(playerid, PROPERTY_OPTION_PREVIEW, "Wejdz (podglad)", options, sizeof(options));
        Properties_AddOption(playerid, PROPERTY_OPTION_BUY, "Kup dom", options, sizeof(options));
    }
    else if(PlayerData[playerid][pPropertyID] == PropertyData[propertyIndex][prSQLID])
    {
        Properties_AddOption(playerid, PROPERTY_OPTION_ENTER, "Wejdz do domu", options, sizeof(options));
        Properties_AddOption(playerid, PROPERTY_OPTION_TOGGLE_LOCK, PropertyData[propertyIndex][prLocked] ? "Otworz drzwi" : "Zamknij drzwi", options, sizeof(options));
        Properties_AddOption(playerid, PROPERTY_OPTION_SET_SPAWN, "Ustaw respawn w domu", options, sizeof(options));
        Properties_AddOption(playerid, PROPERTY_OPTION_SELL, "Sprzedaj dom", options, sizeof(options));
    }
    else
    {
        if(!PropertyData[propertyIndex][prLocked])
        {
            Properties_AddOption(playerid, PROPERTY_OPTION_PREVIEW, "Wejdz (otwarte drzwi)", options, sizeof(options));
        }
    }

    if(PropertyDialogOptionCount[playerid] == 0)
    {
        Properties_AddOption(playerid, PROPERTY_OPTION_NONE, "Brak dostepnych akcji", options, sizeof(options));
    }

    new title[64];
    format(title, sizeof(title), "Nieruchomosc #%d", PropertyData[propertyIndex][prSQLID]);
    ShowPlayerDialog(playerid, DIALOG_PROPERTY_MENU, DIALOG_STYLE_LIST, title, options, "Wybierz", "Zamknij");
    return 1;
}

stock Properties_ShowConfirm(playerid, const message[])
{
    ShowPlayerDialog(playerid, DIALOG_PROPERTY_CONFIRM, DIALOG_STYLE_MSGBOX, "Potwierdzenie", message, "Tak", "Nie");
    return 1;
}

stock Properties_AddOption(playerid, option, const label[], options[], size)
{
    new idx = PropertyDialogOptionCount[playerid];
    if(idx >= sizeof(PropertyDialogOptions[]))
    {
        return 0;
    }
    PropertyDialogOptions[playerid][idx] = option;
    PropertyDialogOptionCount[playerid]++;

    if(idx == 0)
    {
        format(options, size, "%s", label);
    }
    else
    {
        strcat(options, "\n", size);
        strcat(options, label, size);
    }
    return 1;
}

stock Properties_ExecuteAction(playerid, action)
{
    new index = PlayerPropertyTarget[playerid];
    if(index == -1)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Brak wybranej nieruchomosci.");
        return 1;
    }

    switch(action)
    {
        case PROPERTY_OPTION_ENTER:
        {
            Properties_Enter(playerid, index, false);
            return 1;
        }
        case PROPERTY_OPTION_PREVIEW:
        {
            Properties_Enter(playerid, index, true);
            return 1;
        }
        case PROPERTY_OPTION_BUY:
        {
            Properties_AttemptBuy(playerid, index);
            break;
        }
        case PROPERTY_OPTION_SELL:
        {
            Properties_AttemptSell(playerid, index);
            break;
        }
        case PROPERTY_OPTION_TOGGLE_LOCK:
        {
            Properties_ToggleLock(playerid, index);
            break;
        }
        case PROPERTY_OPTION_SET_SPAWN:
        {
            Properties_SetSpawn(playerid, index);
            break;
        }
        }

    if(action == PROPERTY_OPTION_BUY || action == PROPERTY_OPTION_SELL || action == PROPERTY_OPTION_TOGGLE_LOCK || action == PROPERTY_OPTION_SET_SPAWN)
    {
        Properties_ShowMenu(playerid, index);
    }
    return 1;
}

stock Properties_Enter(playerid, index, bool:preview)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    if(PropertyData[index][prOwnerID] != 0 && PropertyData[index][prLocked] && PlayerData[playerid][pPropertyID] != PropertyData[index][prSQLID])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Drzwi sa zamkniete. Nie mozesz wejsc.");
        return 1;
    }

    SetPlayerInterior(playerid, PropertyData[index][prInterior]);
    SetPlayerVirtualWorld(playerid, PropertyData[index][prVirtualWorld]);
    SetPlayerPos(playerid, Float:PropertyData[index][prExitX], Float:PropertyData[index][prExitY], Float:PropertyData[index][prExitZ]);
    SetCameraBehindPlayer(playerid);
    PlayerPropertyInside[playerid] = index;
    PlayerPropertyTarget[playerid] = index;

    if(preview && PropertyData[index][prOwnerID] == 0)
    {
        SendClientMessage(playerid, COLOR_INFO, "Ogladasz wnetrze nieruchomosci. Uzyj /wyjdz aby wrocic.");
    }
    else
    {
        SendClientMessage(playerid, COLOR_INFO, "Wszedles do nieruchomosci.");
    }
    return 1;
}

stock Properties_Exit(playerid, index)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    SetPlayerInterior(playerid, 0);
    SetPlayerVirtualWorld(playerid, 0);
    SetPlayerPos(playerid, Float:PropertyData[index][prEnterX], Float:PropertyData[index][prEnterY], Float:PropertyData[index][prEnterZ]);
    SetCameraBehindPlayer(playerid);
    PlayerPropertyInside[playerid] = -1;
    PlayerPropertyTarget[playerid] = index;
    SendClientMessage(playerid, COLOR_INFO, "Opusciles nieruchomosc.");
    return 1;
}

stock Properties_AttemptBuy(playerid, index)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    if(PlayerData[playerid][pID] <= 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Twoje konto nie jest poprawnie zaladowane.");
        return 1;
    }

    if(PropertyData[index][prOwnerID] != 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Ten dom ma juz wlasciciela.");
        return 1;
    }

    if(PlayerData[playerid][pPropertyID] != 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Posiadasz juz nieruchomosc. Sprzedaj ja najpierw.");
        return 1;
    }

    if(GetPlayerMoney(playerid) < PropertyData[index][prPrice])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie masz wystarczajacej ilosci gotowki.");
        return 1;
    }

    GivePlayerMoney(playerid, -PropertyData[index][prPrice]);
    PlayerData[playerid][pMoney] = GetPlayerMoney(playerid);

    PlayerData[playerid][pPropertyID] = PropertyData[index][prSQLID];
    PlayerData[playerid][pPropertySpawn] = true;
    PlayerData[playerid][pSpawnX] = PropertyData[index][prExitX];
    PlayerData[playerid][pSpawnY] = PropertyData[index][prExitY];
    PlayerData[playerid][pSpawnZ] = PropertyData[index][prExitZ];
    PlayerData[playerid][pSpawnAngle] = 0.0;

    PropertyData[index][prOwnerID] = PlayerData[playerid][pID];
    GetPlayerName(playerid, PropertyData[index][prOwnerName], sizeof(PropertyData[index][prOwnerName]));
    PropertyData[index][prLocked] = 1;
    Properties_RefreshVisual(index);
    PlayerPropertyTarget[playerid] = index;

    new query[256];
    format(query, sizeof(query), "UPDATE properties SET owner_id=%d, locked=1, updated_at=CURRENT_TIMESTAMP WHERE id=%d", PlayerData[playerid][pID], PropertyData[index][prSQLID]);
    Database_Execute(query);

    format(query, sizeof(query), "UPDATE accounts SET property_id=%d, property_spawn=1, spawn_x=%f, spawn_y=%f, spawn_z=%f, spawn_angle=%f WHERE id=%d",
        PropertyData[index][prSQLID], Float:PropertyData[index][prExitX], Float:PropertyData[index][prExitY], Float:PropertyData[index][prExitZ], 0.0, PlayerData[playerid][pID]);
    Database_Execute(query);

    Properties_Log(PropertyData[index][prSQLID], PlayerData[playerid][pID], "BUY", "Zakup nieruchomosci");

    SendClientMessage(playerid, COLOR_SUCCESS, "Zakupiles nieruchomosc. Ustawiono respawn w twoim domu.");
    return 1;
}

stock Properties_AttemptSell(playerid, index)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    if(PlayerData[playerid][pPropertyID] != PropertyData[index][prSQLID])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie jestes wlascicielem tego domu.");
        return 1;
    }

    if(PlayerPropertyInside[playerid] == index)
    {
        Properties_Exit(playerid, index);
    }

    new payout = floatround(PropertyData[index][prPrice] * 0.7, floatround_round);
    GivePlayerMoney(playerid, payout);
    PlayerData[playerid][pMoney] = GetPlayerMoney(playerid);

    PlayerData[playerid][pPropertyID] = 0;
    PlayerData[playerid][pPropertySpawn] = false;
    PlayerData[playerid][pSpawnX] = 1958.3783;
    PlayerData[playerid][pSpawnY] = 1343.1572;
    PlayerData[playerid][pSpawnZ] = 15.3746;
    PlayerData[playerid][pSpawnAngle] = 90.0;

    PropertyData[index][prOwnerID] = 0;
    format(PropertyData[index][prOwnerName], sizeof(PropertyData[index][prOwnerName]), "Brak");
    PropertyData[index][prLocked] = 0;
    Properties_RefreshVisual(index);
    PlayerPropertyTarget[playerid] = index;

    new query[256];
    format(query, sizeof(query), "UPDATE properties SET owner_id=0, locked=0, updated_at=CURRENT_TIMESTAMP WHERE id=%d", PropertyData[index][prSQLID]);
    Database_Execute(query);

    format(query, sizeof(query), "UPDATE accounts SET property_id=0, property_spawn=0, spawn_x=%f, spawn_y=%f, spawn_z=%f, spawn_angle=%f WHERE id=%d",
        1958.3783, 1343.1572, 15.3746, 90.0, PlayerData[playerid][pID]);
    Database_Execute(query);

    Properties_Log(PropertyData[index][prSQLID], PlayerData[playerid][pID], "SELL", "Sprzedaz nieruchomosci");

    new message[144];
    format(message, sizeof(message), "Sprzedales dom za %d$.", payout);
    SendClientMessage(playerid, COLOR_SUCCESS, message);
    return 1;
}

stock Properties_ToggleLock(playerid, index)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    if(PlayerData[playerid][pPropertyID] != PropertyData[index][prSQLID])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie jestes wlascicielem tego domu.");
        return 1;
    }

    PropertyData[index][prLocked] = !PropertyData[index][prLocked];
    Properties_RefreshVisual(index);
    PlayerPropertyTarget[playerid] = index;

    new query[256];
    format(query, sizeof(query), "UPDATE properties SET locked=%d, updated_at=CURRENT_TIMESTAMP WHERE id=%d", PropertyData[index][prLocked], PropertyData[index][prSQLID]);
    Database_Execute(query);

    Properties_Log(PropertyData[index][prSQLID], PlayerData[playerid][pID], PropertyData[index][prLocked] ? "LOCK" : "UNLOCK", "Zmiana stanu drzwi");

    SendClientMessage(playerid, COLOR_SUCCESS, PropertyData[index][prLocked] ? "Zamknales drzwi w swoim domu." : "Otworzyles drzwi w swoim domu.");
    return 1;
}

stock Properties_SetSpawn(playerid, index)
{
    if(index < 0 || index >= PropertyCount)
    {
        return 0;
    }

    if(PlayerData[playerid][pPropertyID] != PropertyData[index][prSQLID])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie jestes wlascicielem tego domu.");
        return 1;
    }

    PlayerData[playerid][pSpawnX] = PropertyData[index][prExitX];
    PlayerData[playerid][pSpawnY] = PropertyData[index][prExitY];
    PlayerData[playerid][pSpawnZ] = PropertyData[index][prExitZ];
    PlayerData[playerid][pSpawnAngle] = 0.0;
    PlayerData[playerid][pPropertySpawn] = true;
    PlayerPropertyTarget[playerid] = index;

    if(PlayerData[playerid][pID] > 0)
    {
        new query[256];
        format(query, sizeof(query), "UPDATE accounts SET spawn_x=%f, spawn_y=%f, spawn_z=%f, spawn_angle=%f, property_spawn=1 WHERE id=%d",
            Float:PropertyData[index][prExitX], Float:PropertyData[index][prExitY], Float:PropertyData[index][prExitZ], 0.0, PlayerData[playerid][pID]);
        Database_Execute(query);
    }

    SendClientMessage(playerid, COLOR_SUCCESS, "Ustawiles respawn wewnatrz domu.");
    return 1;
}

stock Properties_ShowHint(playerid, index)
{
    new message[144];
    if(PropertyData[index][prOwnerID] == 0)
    {
        format(message, sizeof(message), "Dom na sprzedaz: %s | Cena: %d$ | Uzyj /dom", PropertyData[index][prName], PropertyData[index][prPrice]);
    }
    else
    {
        format(message, sizeof(message), "Dom: %s | Wlasciciel: %s | Drzwi: %s | /dom", PropertyData[index][prName], PropertyData[index][prOwnerName], PropertyData[index][prLocked] ? "zamkniete" : "otwarte");
    }
    SendClientMessage(playerid, COLOR_INFO, message);
    return 1;
}

stock Properties_FindByPickup(pickupid)
{
    for(new i = 0; i < PropertyCount; i++)
    {
        if(PropertyData[i][prPickup] == pickupid)
        {
            return i;
        }
    }
    return -1;
}

stock Properties_FindBySQLID(sqlid)
{
    for(new i = 0; i < PropertyCount; i++)
    {
        if(PropertyData[i][prSQLID] == sqlid)
        {
            return i;
        }
    }
    return -1;
}

stock Properties_FindNearest(playerid, Float:range)
{
    new nearest = -1;
    new Float:bestDistance = range;

    for(new i = 0; i < PropertyCount; i++)
    {
        new Float:distance = GetPlayerDistanceFromPoint(playerid, Float:PropertyData[i][prEnterX], Float:PropertyData[i][prEnterY], Float:PropertyData[i][prEnterZ]);
        if(distance <= bestDistance)
        {
            bestDistance = distance;
            nearest = i;
        }
    }
    return nearest;
}

stock Properties_SeedDefaults()
{
    new query[128];
    format(query, sizeof(query), "SELECT COUNT(*) AS count FROM properties");
    new DBResult:result = db_query(gDatabaseHandle, query);

    if(!result)
    {
        return 0;
    }

    db_next_row(result);
    new count = Database_FetchInt(result, "count");
    db_free_result(result);

    if(count > 0)
    {
        return 1;
    }

    Properties_InsertSeed("Idlewood Apartament", 120000, 3, 2031.1562, -1119.0286, 26.3047, 235.5084, 1189.1699, 1080.3398);
    Properties_InsertSeed("Willowfield Dom", 150000, 1, 2485.4966, -1692.2699, 14.7656, 223.1561, 1287.0870, 1082.1406);
    Properties_InsertSeed("Marina Mieszkanie", 210000, 3, 812.8632, -1606.6682, 13.5469, 1527.2290, -11.5741, 1002.0971);
    Properties_InsertSeed("Richman Rezydencja", 320000, 5, 1305.3121, -797.8125, 84.1406, 140.2670, 1366.2188, 1083.8633);
    Properties_InsertSeed("Las Venturas Penthouse", 400000, 10, 2496.0273, 918.6331, 11.0156, 201.3653, 162.3589, 1003.0300);
    return 1;
}

stock Properties_InsertSeed(const name[], price, interior, Float:enterX, Float:enterY, Float:enterZ, Float:exitX, Float:exitY, Float:exitZ)
{
    new escapedName[128];
    Database_Escape(name, escapedName, sizeof(escapedName));

    new query[512];
    format(query, sizeof(query), "INSERT INTO properties (name, price, owner_id, locked, interior, enter_x, enter_y, enter_z, exit_x, exit_y, exit_z) VALUES ('%s', %d, 0, 0, %d, %f, %f, %f, %f, %f, %f)", escapedName, price, interior, enterX, enterY, enterZ, exitX, exitY, exitZ);
    Database_Execute(query);
    return 1;
}

stock Properties_Log(propertySQLID, accountID, const action[], const details[])
{
    new escapedDetails[256];
    Database_Escape(details, escapedDetails, sizeof(escapedDetails));

    new query[512];
    format(query, sizeof(query), "INSERT INTO property_logs (property_id, account_id, action, details) VALUES (%d, %d, '%s', '%s')", propertySQLID, accountID, action, escapedDetails);
    Database_Execute(query);
    return 1;
}

stock Properties_GetPropertyName(sqlid, output[], size)
{
    for(new i = 0; i < PropertyCount; i++)
    {
        if(PropertyData[i][prSQLID] == sqlid)
        {
            format(output, size, "%s", PropertyData[i][prName]);
            return 1;
        }
    }

    format(output, size, "Brak");
    return 0;
}
